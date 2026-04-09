import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import create_retriever_tool

from pydantic import Field
from app.core import config

class CustomFAISSSQLiteRetriever(BaseRetriever):
    """
    Công cụ truy xuất được thiết kế riêng để đọc schema SQLite + FAISS của team Data.
    """
    sqlite_path: str = Field(default=config.SQLITE_PATH)
    faiss_path: str = Field(default=config.FAISS_PATH)
    model_name: str = Field(default=config.EMBEDDING_MODEL)
    k: int = Field(default=3)

    # Private attributes để không bị Pydantic parse
    _index: faiss.Index = None
    _model: SentenceTransformer = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load FAISS index và Model Embedding ngay khi khởi tạo
        self._index = faiss.read_index(self.faiss_path)
        self._model = SentenceTransformer(self.model_name)

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        # Bước 1: Mã hóa câu hỏi thành Vector
        query_vector = self._model.encode(
            [query], 
            convert_to_numpy=True, 
            normalize_embeddings=True
        )
        query_vector = np.asarray(query_vector, dtype=np.float32)

        # Bước 2: Tìm top K id trong FAISS
        distances, indices = self._index.search(query_vector, self.k)
        faiss_row_ids = indices[0].tolist()

        # Bước 3: Dùng ID tìm nội dung gốc trong SQLite
        docs = []
        conn = sqlite3.connect(self.sqlite_path)
        try:
            # Tạo câu lệnh SQL động với mệnh đề IN (...)
            placeholders = ",".join("?" * len(faiss_row_ids))
            query_sql = f"""
                SELECT c.section_title, c.content 
                FROM chunks c
                JOIN faiss_index_map f ON c.id = f.chunk_id
                WHERE f.faiss_row_id IN ({placeholders})
            """
            cursor = conn.execute(query_sql, faiss_row_ids)
            rows = cursor.fetchall()

            for row in rows:
                title, content = row
                docs.append(Document(
                    page_content=content,
                    metadata={"source": title} # Gắn title làm metadata trích dẫn
                ))
        finally:
            conn.close()

        return docs

def get_xanh_sm_retriever():
    # Khởi tạo custom retriever
    retriever = CustomFAISSSQLiteRetriever(k=3)
    
    # Biến nó thành tool cho LangGraph Agent
    return create_retriever_tool(
        retriever,
        "policy_search",
        "Dùng để tra cứu quy định, giá cước, chính sách thú cưng, hành lý, và quy tắc tài xế của Xanh SM."
    )

# Export thành list để file agent_graph.py gọi vào
list_of_tools = [get_xanh_sm_retriever()]