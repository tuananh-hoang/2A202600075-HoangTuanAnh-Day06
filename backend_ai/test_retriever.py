"""
test_retrieval.py
Chạy: python test_retrieval.py
So sánh CustomFAISSSQLiteRetriever (cũ) vs HybridRAGRetriever (mới).
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

from app.utils.vector_tools import CustomFAISSSQLiteRetriever
from app.utils.retrieval_advanced import HybridRAGRetriever
from app.core import config


TEST_QUERIES = [
    "Điều khoản sử dụng dịch vụ Xanh SM?",
    "Chính sách thú cưng trên xe?",
    "Mức giá cước tính như thế nào?",
]


def _print_docs(results, label: str):
    print(f"\n{'─'*50}")
    print(f"  {label}  ({len(results)} kết quả)")
    print(f"{'─'*50}")
    for i, doc in enumerate(results, start=1):
        source = doc.metadata.get("source", "Unknown")
        rerank = doc.metadata.get("rerank_score")
        score_str = f" | rerank={rerank}" if rerank is not None else ""
        content_preview = (
            doc.page_content[:300] + "..." if len(doc.page_content) > 300
            else doc.page_content
        )
        print(f"\n[{i}] Nguồn: {source}{score_str}")
        print(f"    {content_preview}")


def check_files() -> bool:
    ok = True
    for path, label in [(config.FAISS_PATH, "FAISS"), (config.SQLITE_PATH, "SQLite")]:
        if os.path.exists(path):
            print(f"✅ {label}: {path}")
        else:
            print(f"❌ Không tìm thấy {label}: {path}")
            ok = False
    return ok


def run_test():
    print("=" * 55)
    print("  TEST RETRIEVAL — CŨ vs HYBRID RAG")
    print("=" * 55)

    if not check_files():
        return

    # ── Khởi tạo retriever cũ ──
    print("\n⏳ Khởi tạo CustomFAISSSQLiteRetriever (cũ)...")
    try:
        old_retriever = CustomFAISSSQLiteRetriever(k=3)
        print("✅ Retriever cũ sẵn sàng.")
    except Exception as e:
        print(f"❌ Không khởi tạo được retriever cũ: {e}")
        old_retriever = None

    # ── Khởi tạo retriever mới ──
    print("\n⏳ Khởi tạo HybridRAGRetriever (mới)...")
    try:
        new_retriever = HybridRAGRetriever(candidate_k=20, final_k=5)
        print("✅ HybridRAGRetriever sẵn sàng.")
    except Exception as e:
        print(f"❌ Không khởi tạo được HybridRAGRetriever: {e}")
        new_retriever = None

    # ── Chạy từng query ──
    for query in TEST_QUERIES:
        print(f"\n\n{'═'*55}")
        print(f"❓ Query: {query}")

        if old_retriever:
            t0 = time.perf_counter()
            old_docs = old_retriever._get_relevant_documents(query, run_manager=None)
            old_ms = (time.perf_counter() - t0) * 1000
            _print_docs(old_docs, f"CŨ — FAISS only | {old_ms:.0f} ms")

        if new_retriever:
            t0 = time.perf_counter()
            new_docs = new_retriever._get_relevant_documents(query, run_manager=None)
            new_ms = (time.perf_counter() - t0) * 1000
            _print_docs(new_docs, f"MỚI — Hybrid + Rerank | {new_ms:.0f} ms")

    print(f"\n{'='*55}")
    print("  DONE")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run_test()