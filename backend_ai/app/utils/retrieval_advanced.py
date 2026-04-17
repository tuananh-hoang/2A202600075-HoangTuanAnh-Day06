"""
retrieval_advanced.py
Hybrid Search (BM25 + FAISS) + RRF
Dùng OpenAI Embeddings thay sentence_transformers → loại bỏ PyTorch khỏi image.

⚠️  LƯU Ý QUAN TRỌNG khi migrate:
    - Model cũ (all-MiniLM-L6-v2) → vector 384 chiều
    - Model mới (text-embedding-3-small) → vector 1536 chiều
    - Bắt buộc rebuild FAISS index bằng setup_db.py trước khi deploy.

Đặt file này tại: backend_ai/app/retrieval_advanced.py
Sau đó sửa tools.py: from app.retrieval_advanced import get_xanh_sm_retriever
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
from openai import OpenAI
from pydantic import Field, PrivateAttr
from rank_bm25 import BM25Okapi

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

    def __init__(
        self,
        chunk_id: int,
        section_title: str,
        content: str,
        url: str = "",
        score: float = 0.0,
    ):
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
    Hybrid RAG dùng OpenAI Embeddings (dense) + BM25 (sparse) + RRF.
    Không còn phụ thuộc sentence_transformers hay PyTorch.

    Pipeline:
        FAISS (OpenAI dense)  ─┐
        BM25  (sparse)        ─┤→ RRF → top final_k Documents
    """

    # ── Pydantic fields ──
    sqlite_path: str = Field(default=config.SQLITE_PATH)
    faiss_path: str = Field(default=config.FAISS_PATH)

    # OpenAI embedding model — text-embedding-3-small: nhanh, rẻ, 1536 chiều
    # text-embedding-3-large: chính xác hơn, 3072 chiều, đắt hơn ~3x
    embedding_model: str = Field(default="text-embedding-3-small")

    # Số candidates mỗi retriever trước khi merge
    candidate_k: int = Field(default=20)
    # Số chunks thực sự trả về sau RRF
    final_k: int = Field(default=5)

    # ── Private attributes ──
    _client: OpenAI = PrivateAttr()
    _faiss_index: faiss.Index = PrivateAttr()
    _bm25: BM25Okapi = PrivateAttr()
    _bm25_idx_to_chunk_id: list[int] = PrivateAttr(default_factory=list)
    _faiss_row_to_chunk_id: dict[int, int] = PrivateAttr(default_factory=dict)
    _chunk_cache: dict[int, _Candidate] = PrivateAttr(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # OpenAI client — dùng key từ config (OPENAI_API_KEY env var)
        # Nếu không có key, set None (sẽ dùng mock LLM)
        from app.core.config import settings
        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)
        else:
            self._client = None  # Mock LLM mode

        # Load FAISS index
        self._faiss_index = faiss.read_index(self.faiss_path)

        # Load SQLite corpus → build BM25 + caches
        self._load_from_sqlite()

    # ──────────────────────────────────────────────
    # KHỞI TẠO DỮ LIỆU TỪ SQLITE
    # ──────────────────────────────────────────────

    def _load_from_sqlite(self) -> None:
        """
        Load 1 lần khi service khởi động.
        Build BM25 index và cache toàn bộ chunk content trong RAM.
        """
        conn = sqlite3.connect(self.sqlite_path)
        try:
            rows = conn.execute(
                "SELECT faiss_row_id, chunk_id FROM faiss_index_map ORDER BY faiss_row_id"
            ).fetchall()
            self._faiss_row_to_chunk_id = {int(r[0]): int(r[1]) for r in rows}

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

            self._chunk_cache[chunk_id] = _Candidate(
                chunk_id=chunk_id,
                section_title=section_title,
                content=content,
                url=url or "",
            )

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
    # DENSE SEARCH (FAISS + OpenAI Embeddings)
    # ──────────────────────────────────────────────

    def _embed_query(self, query: str) -> np.ndarray:
        """
        Gọi OpenAI Embeddings API để encode query.
        Trả về vector float32 đã normalize (chuẩn bị cho cosine search).
        """
        response = self._client.embeddings.create(
            input=query,
            model=self.embedding_model,
        )
        vec = np.array(response.data[0].embedding, dtype=np.float32)
        # Normalize để dùng với IndexFlatIP (inner product = cosine khi normalized)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def _dense_search(self, query: str) -> list[tuple[int, float]]:
        """Trả về list (chunk_id, cosine_score), sắp xếp giảm dần."""
        q_vec = self._embed_query(query).reshape(1, -1)
        scores, faiss_row_ids = self._faiss_index.search(q_vec, self.candidate_k)

        results: list[tuple[int, float]] = []
        for row_id, score in zip(faiss_row_ids[0].tolist(), scores[0].tolist()):
            if row_id == -1:
                continue
            chunk_id = self._faiss_row_to_chunk_id.get(int(row_id))
            if chunk_id is not None:
                results.append((chunk_id, float(score)))
        return results

    # ──────────────────────────────────────────────
    # SPARSE SEARCH (BM25)
    # ──────────────────────────────────────────────

    def _sparse_search(self, query: str) -> list[tuple[int, float]]:
        """Trả về list (chunk_id, bm25_score), sắp xếp giảm dần."""
        tokens = query.lower().split()
        raw_scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(raw_scores)[::-1][: self.candidate_k]
        return [
            (self._bm25_idx_to_chunk_id[int(i)], float(raw_scores[i]))
            for i in top_indices
            if raw_scores[i] > 0
        ]

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

        # Bước 1: dense (OpenAI) + sparse (BM25)
        dense_results = self._dense_search(query)
        sparse_results = self._sparse_search(query)

        # Bước 2: RRF merge
        merged = _rrf_merge(dense_results, sparse_results)

        # Bước 3: lấy top candidates từ cache
        docs: List[Document] = []
        for chunk_id, rrf_score in merged[: self.final_k]:
            cand = self._chunk_cache.get(chunk_id)
            if cand is None:
                continue
            docs.append(
                Document(
                    page_content=cand.content,
                    metadata={
                        "source": cand.section_title,
                        "chunk_id": cand.chunk_id,
                        "url": cand.url,
                        "rrf_score": round(rrf_score, 6),
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
# FACTORY
# ──────────────────────────────────────────────────────────────────────

def get_xanh_sm_retriever(
    candidate_k: int = 20,
    final_k: int = 5,
    embedding_model: str = "text-embedding-3-small",
):
    """
    Drop-in replacement cho get_xanh_sm_retriever() cũ trong tools.py.

    Thay đổi duy nhất cần làm trong tools.py:
        from app.retrieval_advanced import get_xanh_sm_retriever
    """
    retriever = HybridRAGRetriever(
        candidate_k=candidate_k,
        final_k=final_k,
        embedding_model=embedding_model,
    )
    return create_retriever_tool(
        retriever,
        "policy_search",
        "Dùng để tra cứu quy định, giá cước, chính sách thú cưng, hành lý, "
        "và quy tắc tài xế của Xanh SM.",
    )


_retriever_tool_cache = None

def get_tools() -> list:
    global _retriever_tool_cache
    if _retriever_tool_cache is None:
        _retriever_tool_cache = [get_xanh_sm_retriever()]
    return _retriever_tool_cache
