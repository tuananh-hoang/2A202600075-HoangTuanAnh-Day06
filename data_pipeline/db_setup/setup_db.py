"""Build SQLite + FAISS stores from chunked policy data.

Expected input is JSONL from ``data_pipeline/processed_data/process_data.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


CHUNKS_JSONL_DEFAULT = Path(__file__).resolve().parents[1] / "processed_data" / "chunks.jsonl"
SQLITE_PATH_DEFAULT = Path(__file__).resolve().parent / "knowledge_base.sqlite"
FAISS_PATH_DEFAULT = Path(__file__).resolve().parent / "knowledge_base.faiss"
MODEL_NAME_DEFAULT = "paraphrase-multilingual-MiniLM-L12-v2"
GENERAL_TERMS_BASE_URL = "https://www.xanhsm.com/terms-policies/general?terms="
PRICE_NEWS_URL = "https://www.xanhsm.com/news/gia-taxi-xanh-sm-bao-nhieu"


def resolve_source_url(filename: str, fallback_path: str) -> str:
    stem = Path(filename).stem
    prefix = stem.split("_", 1)[0]

    if prefix.isdigit():
        file_number = int(prefix)
        if 1 <= file_number <= 15:
            return f"{GENERAL_TERMS_BASE_URL}{file_number}"
        if file_number == 16:
            return PRICE_NEWS_URL

    return fallback_path


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    items: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            source_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            section_title TEXT,
            section_chunk_index INTEGER,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            char_count INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE(document_id, chunk_index)
        );

        CREATE TABLE IF NOT EXISTS embeddings (
            chunk_id INTEGER PRIMARY KEY,
            model_name TEXT NOT NULL,
            dimension INTEGER NOT NULL,
            vector BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS faiss_index_map (
            faiss_row_id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def upsert_document(conn: sqlite3.Connection, doc_id: str, filename: str, source_path: str) -> int:
    conn.execute(
        """
        INSERT INTO documents (doc_id, filename, source_path)
        VALUES (?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
            filename = excluded.filename,
            source_path = excluded.source_path
        """,
        (doc_id, filename, source_path),
    )
    doc_row = conn.execute("SELECT id FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if doc_row is None:
        raise RuntimeError(f"Cannot fetch document row for doc_id={doc_id}")
    return int(doc_row[0])


def upsert_chunk(
    conn: sqlite3.Connection,
    document_id: int,
    chunk_index: int,
    section_title: str,
    section_chunk_index: int,
    content: str,
    char_count: int,
) -> int:
    # Include document/chunk identity so repeated policy text across files
    # does not violate UNIQUE(content_hash).
    content_hash = hashlib.sha256(f"{document_id}:{chunk_index}:{content}".encode("utf-8")).hexdigest()
    conn.execute(
        """
        INSERT INTO chunks (
            document_id,
            chunk_index,
            section_title,
            section_chunk_index,
            content,
            content_hash,
            char_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id, chunk_index) DO UPDATE SET
            section_title = excluded.section_title,
            section_chunk_index = excluded.section_chunk_index,
            content = excluded.content,
            content_hash = excluded.content_hash,
            char_count = excluded.char_count
        """,
        (
            document_id,
            chunk_index,
            section_title,
            section_chunk_index,
            content,
            content_hash,
            char_count,
        ),
    )

    chunk_row = conn.execute(
        "SELECT id FROM chunks WHERE document_id = ? AND chunk_index = ?",
        (document_id, chunk_index),
    ).fetchone()
    if chunk_row is None:
        raise RuntimeError(f"Cannot fetch chunk row for document_id={document_id}, chunk_index={chunk_index}")
    return int(chunk_row[0])


def build_embedding_text(section_title: str, content: str) -> str:
    # Add section signal for better retrieval precision on policy documents.
    return f"passage: {section_title}\n{content}".strip()


def batched(iterable: Sequence[Tuple[int, str]], batch_size: int) -> Iterable[Sequence[Tuple[int, str]]]:
    for idx in range(0, len(iterable), batch_size):
        yield iterable[idx : idx + batch_size]


def insert_embeddings_and_faiss(
    conn: sqlite3.Connection,
    model: SentenceTransformer,
    chunk_texts: Sequence[Tuple[int, str]],
    model_name: str,
    faiss_path: Path,
    batch_size: int,
) -> None:
    vectors: List[np.ndarray] = []
    chunk_ids: List[int] = []

    for batch in batched(chunk_texts, batch_size=batch_size):
        ids = [chunk_id for chunk_id, _ in batch]
        texts = [text for _, text in batch]

        emb = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        emb = np.asarray(emb, dtype=np.float32)

        for row_idx, chunk_id in enumerate(ids):
            vector = emb[row_idx]
            vectors.append(vector)
            chunk_ids.append(chunk_id)
            conn.execute(
                """
                INSERT INTO embeddings (chunk_id, model_name, dimension, vector)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    model_name = excluded.model_name,
                    dimension = excluded.dimension,
                    vector = excluded.vector,
                    created_at = CURRENT_TIMESTAMP
                """,
                (chunk_id, model_name, int(vector.shape[0]), vector.tobytes()),
            )

    conn.commit()

    if not vectors:
        raise RuntimeError("No vectors were generated")

    matrix = np.vstack(vectors).astype(np.float32)
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    faiss.write_index(index, str(faiss_path))

    conn.execute("DELETE FROM faiss_index_map")
    conn.executemany(
        "INSERT INTO faiss_index_map (faiss_row_id, chunk_id) VALUES (?, ?)",
        [(row_id, chunk_id) for row_id, chunk_id in enumerate(chunk_ids)],
    )
    conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create SQLite + FAISS knowledge stores from chunks")
    parser.add_argument("--chunks-file", type=Path, default=CHUNKS_JSONL_DEFAULT, help="Input chunks JSONL")
    parser.add_argument("--sqlite-path", type=Path, default=SQLITE_PATH_DEFAULT, help="Output SQLite DB path")
    parser.add_argument("--faiss-path", type=Path, default=FAISS_PATH_DEFAULT, help="Output FAISS index path")
    parser.add_argument("--model-name", type=str, default=MODEL_NAME_DEFAULT, help="SentenceTransformer model")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    args.faiss_path.parent.mkdir(parents=True, exist_ok=True)

    raw_chunks = load_jsonl(args.chunks_file)
    if not raw_chunks:
        raise RuntimeError("No chunks found in input JSONL")

    conn = sqlite3.connect(args.sqlite_path)
    try:
        ensure_schema(conn)

        chunk_texts: List[Tuple[int, str]] = []
        for item in raw_chunks:
            doc_id = str(item["doc_id"])
            filename = str(item["filename"])
            source_path = resolve_source_url(filename=filename, fallback_path=str(item["source_path"]))
            chunk_index = int(item["chunk_index"])
            section_title = str(item.get("section_title", ""))
            section_chunk_index = int(item.get("section_chunk_index", 0))
            content = str(item["text"])
            char_count = int(item.get("char_count", len(content)))

            document_id = upsert_document(conn, doc_id=doc_id, filename=filename, source_path=source_path)
            chunk_id = upsert_chunk(
                conn,
                document_id=document_id,
                chunk_index=chunk_index,
                section_title=section_title,
                section_chunk_index=section_chunk_index,
                content=content,
                char_count=char_count,
            )
            chunk_texts.append((chunk_id, build_embedding_text(section_title=section_title, content=content)))

        conn.commit()

        model = SentenceTransformer(args.model_name)
        insert_embeddings_and_faiss(
            conn=conn,
            model=model,
            chunk_texts=chunk_texts,
            model_name=args.model_name,
            faiss_path=args.faiss_path,
            batch_size=args.batch_size,
        )
    finally:
        conn.close()

    print(f"Inserted/updated {len(raw_chunks)} chunks")
    print(f"SQLite DB: {args.sqlite_path}")
    print(f"FAISS index: {args.faiss_path}")
    print(f"Embedding model: {args.model_name}")


if __name__ == "__main__":
    main()