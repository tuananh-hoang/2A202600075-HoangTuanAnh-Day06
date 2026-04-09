"""
retrieval_advanced.py
Nâng cấp RAG: Hybrid Search (BM25 + FAISS) + RRF + Cross-Encoder Reranker
Tương thích hoàn toàn với schema SQLite/FAISS từ setup_db.py của team Data.

Đặt file này tại: backend_ai/app/retrieval_advanced.py
Sau đó sửa tools.py: thay CustomFAISSSQLiteRetriever → HybridRAGRetriever
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import List

import faiss
import numpy as np
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import create_retriever_tool
from pydantic import Field, PrivateAttr
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from app.core import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# INTERNAL DATA CLASS
# ──────────────────────────────────────────────────────────────────────

class _Candidate:
    """
    Đơn vị nội bộ trong pipeline trước khi chuyển sang LangChain Document.
    Dùng class thay dataclass để tránh conflict với Pydantic của BaseRetriever.
    """
    __slots__ = ("chunk_id", "section_title", "content", "url", "score")

    def __init__(self, chunk_id: int, section_title: str, content: str, url: str = "", score: float = 0.0):
        self.chunk_id = chunk_id
        self.section_title = section_title
        self.content = content
        self.url = url
        self.score = score


# ──────────────────────────────────────────────────────────────────────
# RECIPROCAL RANK FUSION
# ──────────────────────────────────────────────────────────────────────

def _rrf_merge(
    *ranked_lists: list[tuple[int, float]],
    k: int = 60,
) -> list[tuple[int, float]]:
    """
    Hợp nhất nhiều ranked list bằng Reciprocal Rank Fusion.

    Mỗi phần tử trong ranked_list là (chunk_id, score).
    Score gốc bị bỏ qua — chỉ dùng rank.

    RRF(d) = Σ_r  1 / (k + rank_r(d))
    k=60: giá trị mặc định từ bài báo gốc Cormack et al. 2009.
    """
    accumulator: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (chunk_id, _) in enumerate(ranked, start=1):
            accumulator[chunk_id] = accumulator.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(accumulator.items(), key=lambda x: x[1], reverse=True)


# ──────────────────────────────────────────────────────────────────────
# HYBRID RAG RETRIEVER
# ──────────────────────────────────────────────────────────────────────

class HybridRAGRetriever(BaseRetriever):
    """
    Drop-in replacement cho CustomFAISSSQLiteRetriever.
    Giao diện giữ nguyên (BaseRetriever → list[Document]),
    bên trong thêm 3 lớp nâng cấp:

      FAISS (dense)  ─┐
      BM25  (sparse) ─┤→ RRF → CrossEncoder Reranker → top final_k
    """

    # ── Pydantic fields (khai báo public, Pydantic sẽ validate) ──
    sqlite_path: str = Field(default=config.SQLITE_PATH)
    faiss_path: str = Field(default=config.FAISS_PATH)
    model_name: str = Field(default=config.EMBEDDING_MODEL)

    # Số candidates mỗi retriever trước khi merge — đặt lớn hơn final_k
    candidate_k: int = Field(default=20)
    # Số chunks thực sự trả về sau rerank
    final_k: int = Field(default=5)

    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description=(
            "Model cross-encoder. Với corpus tiếng Việt nặng, "
            "cân nhắc: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        ),
    )

    # ── Private attributes — Pydantic không serialize ──
    _faiss_index: faiss.Index = PrivateAttr()
    _embed_model: SentenceTransformer = PrivateAttr()
    _reranker: CrossEncoder = PrivateAttr()
    _bm25: BM25Okapi = PrivateAttr()

    # Map: vị trí trong BM25 corpus (0-indexed) → chunk_id trong SQLite
    _bm25_idx_to_chunk_id: list[int] = PrivateAttr(default_factory=list)
    # Map: faiss_row_id → chunk_id (load 1 lần lúc khởi tạo)
    _faiss_row_to_chunk_id: dict[int, int] = PrivateAttr(default_factory=dict)
    # Cache nội dung chunk: chunk_id → _Candidate (tránh query SQLite lặp)
    _chunk_cache: dict[int, _Candidate] = PrivateAttr(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Bước 1: load FAISS index từ disk
        self._faiss_index = faiss.read_index(self.faiss_path)

        # Bước 2: load embedding model
        self._embed_model = SentenceTransformer(self.model_name)

        # Bước 3: load cross-encoder reranker
        logger.info("Loading reranker: %s", self.reranker_model)
        self._reranker = CrossEncoder(self.reranker_model)

        # Bước 4: load toàn bộ corpus từ SQLite, build BM25 + cache + faiss map
        self._load_from_sqlite()

    # ──────────────────────────────────────────────
    # KHỞI TẠO DỮ LIỆU TỪ SQLITE
    # ──────────────────────────────────────────────

    def _load_from_sqlite(self) -> None:
        """
        Load 1 lần duy nhất khi service khởi động.
        SQLite corpus nhỏ (policy docs) nên giữ toàn bộ trong RAM là hợp lý.
        Nếu corpus > vài trăm MB thì cần streaming BM25 hoặc Elasticsearch.
        """
        conn = sqlite3.connect(self.sqlite_path)
        try:
            # Load faiss_index_map: faiss_row_id → chunk_id
            rows = conn.execute(
                "SELECT faiss_row_id, chunk_id FROM faiss_index_map ORDER BY faiss_row_id"
            ).fetchall()
            self._faiss_row_to_chunk_id = {int(r[0]): int(r[1]) for r in rows}

            # Load tất cả chunks để build BM25 và cache nội dung
            # JOIN với documents để lấy source_path (URL)
            chunk_rows = conn.execute(
                """
                SELECT c.id, c.section_title, c.content, d.source_path 
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY c.id
                """
            ).fetchall()

        finally:
            conn.close()

        tokenized_corpus: list[list[str]] = []
        self._bm25_idx_to_chunk_id = []

        for chunk_id, section_title, content, url in chunk_rows:
            chunk_id = int(chunk_id)
            section_title = section_title or ""
            content = content or ""

            # Cache candidate
            self._chunk_cache[chunk_id] = _Candidate(
                chunk_id=chunk_id,
                section_title=section_title,
                content=content,
                url=url or "",
            )

            # BM25: tokenize đơn giản bằng whitespace
            # Cho tiếng Việt: thay bằng underthesea.word_tokenize nếu cần độ chính xác cao hơn
            bm25_text = f"{section_title} {content}".lower()
            tokenized_corpus.append(bm25_text.split())
            self._bm25_idx_to_chunk_id.append(chunk_id)

        self._bm25 = BM25Okapi(tokenized_corpus)
        logger.info(
            "HybridRAGRetriever init: %d chunks loaded, BM25 built, FAISS ntotal=%d",
            len(chunk_rows),
            self._faiss_index.ntotal,
        )

    # ──────────────────────────────────────────────
    # DENSE SEARCH (FAISS)
    # ──────────────────────────────────────────────

    def _dense_search(self, query: str) -> list[tuple[int, float]]:
        """
        Trả về list (chunk_id, cosine_score), sắp xếp giảm dần.

        Encode query KHÔNG thêm prefix "passage:" vì đây là query, không phải document.
        Model paraphrase-multilingual-MiniLM không dùng asymmetric prefix,
        khác với e5/bge cần "query: " / "passage: ".
        """
        q_vec = self._embed_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)

        scores, faiss_row_ids = self._faiss_index.search(q_vec, self.candidate_k)

        results: list[tuple[int, float]] = []
        for row_id, score in zip(faiss_row_ids[0].tolist(), scores[0].tolist()):
            if row_id == -1:            # FAISS trả -1 nếu index có ít hơn k entries
                continue
            chunk_id = self._faiss_row_to_chunk_id.get(int(row_id))
            if chunk_id is not None:
                results.append((chunk_id, float(score)))
        return results

    # ──────────────────────────────────────────────
    # SPARSE SEARCH (BM25)
    # ──────────────────────────────────────────────

    def _sparse_search(self, query: str) -> list[tuple[int, float]]:
        """
        Trả về list (chunk_id, bm25_score), sắp xếp giảm dần.
        BM25 tốt với từ khóa chính xác: tên quy định, mức giá, điều khoản cụ thể.
        """
        tokens = query.lower().split()
        raw_scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(raw_scores)[::-1][: self.candidate_k]
        return [
            (self._bm25_idx_to_chunk_id[int(i)], float(raw_scores[i]))
            for i in top_indices
            if raw_scores[i] > 0          # lọc chunk có score = 0 (không liên quan)
        ]

    # ──────────────────────────────────────────────
    # RERANKER
    # ──────────────────────────────────────────────

    def _rerank(self, query: str, candidates: list[_Candidate]) -> list[_Candidate]:
        """
        CrossEncoder chấm điểm từng cặp (query, content).
        Chỉ chạy trên candidate_k chunks đã qua RRF — không scan toàn corpus.
        """
        if not candidates:
            return []
        pairs = [(query, c.content) for c in candidates]
        scores: np.ndarray = self._reranker.predict(pairs)
        for cand, score in zip(candidates, scores.tolist()):
            cand.score = float(score)
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    # ──────────────────────────────────────────────
    # ENTRY POINT — giao diện BaseRetriever
    # ──────────────────────────────────────────────

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        t0 = time.perf_counter()

        # Bước 1: dense + sparse retrieval
        dense_results  = self._dense_search(query)
        sparse_results = self._sparse_search(query)

        # Bước 2: RRF merge → list (chunk_id, rrf_score)
        merged = _rrf_merge(dense_results, sparse_results)

        # Bước 3: lấy _Candidate từ cache cho top merged
        candidates: list[_Candidate] = []
        for chunk_id, _ in merged[: self.candidate_k]:
            cand = self._chunk_cache.get(chunk_id)
            if cand is not None:
                candidates.append(cand)

        # Bước 4: cross-encoder rerank
        reranked = self._rerank(query, candidates)

        # Bước 5: chuyển sang LangChain Document (giữ nguyên schema cũ)
        docs: List[Document] = []
        for cand in reranked[: self.final_k]:
            docs.append(
                Document(
                    page_content=cand.content,
                    metadata={
                        "source": cand.section_title,
                        "chunk_id": cand.chunk_id,
                        "url": cand.url,
                        "rerank_score": round(cand.score, 4),
                    },
                )
            )

        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "HybridRAGRetriever | query='%.60s' | dense=%d sparse=%d merged=%d final=%d | %.1f ms",
            query,
            len(dense_results),
            len(sparse_results),
            len(merged),
            len(docs),
            latency_ms,
        )
        return docs


# ──────────────────────────────────────────────────────────────────────
# FACTORY — thay thế get_xanh_sm_retriever() trong tools.py
# ──────────────────────────────────────────────────────────────────────

def get_xanh_sm_retriever(
    candidate_k: int = 20,
    final_k: int = 5,
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
):
    """
    Drop-in replacement cho get_xanh_sm_retriever() cũ trong tools.py.

    Thay đổi duy nhất cần làm trong tools.py:
        from app.retrieval_advanced import get_xanh_sm_retriever
    (xóa import từ file tools cũ)
    """
    retriever = HybridRAGRetriever(
        candidate_k=candidate_k,
        final_k=final_k,
        reranker_model=reranker_model,
    )
    return create_retriever_tool(
        retriever,
        "policy_search",
        "Dùng để tra cứu quy định, giá cước, chính sách thú cưng, hành lý, "
        "và quy tắc tài xế của Xanh SM.",
    )


list_of_tools = [get_xanh_sm_retriever()]