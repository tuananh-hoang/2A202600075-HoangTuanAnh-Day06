# Chatbot Tai Xe Xanh SM

Tai lieu goc cho dev trong team de setup, chay va nang cap luong RAG `v3`.

Kien truc muc tieu hien tai:

`data_pipeline -> SQLite/FAISS -> backend agent LangGraph -> frontend Streamlit`

README nay lay `v3` lam huong chinh, nhung van ghi ro cac cho wiring hien tai chua dong bo de tranh chay nham entrypoint.

## 1. Muc tieu du an

He thong ho tro tai xe Xanh SM theo mo hinh RAG:

- Thu thap va xu ly tai lieu chinh sach.
- Build knowledge base dang `SQLite + FAISS`.
- Backend dung LangGraph de classify, retrieve, answer, va escalate khi do tin cay thap.
- Frontend Streamlit goi API `/chat` de demo hoi dap.

## 2. Cau truc thu muc quan trong

### Data pipeline

- `data_pipeline/scrapers/test_crawl.py`
  - Crawl noi dung policy tu website Xanh SM va luu ra Markdown trong `data_pipeline/raw_data/`.
- `data_pipeline/processed_data/`
  - Noi dat `chunks.jsonl` sau khi xu ly du lieu.
- `data_pipeline/db_setup/setup_db.py`
  - Build `knowledge_base.sqlite` va `knowledge_base.faiss` tu `chunks.jsonl`.
  - Sinh embedding bang `sentence-transformers`.

### Backend AI

- `backend_ai/app/main.py`
  - API cu / runtime co ban.
- `backend_ai/app/main_v2.py`
  - Ban trung gian: tool-calling graph co `thread_id` memory.
- `backend_ai/app/main_v3.py`
  - API schema moi nhat de tham chieu tai lieu.
  - Bo sung `confidence`, `query_type`, `escalate`, `sources`, `feedback`.
- `backend_ai/app/core/agent_graph.py`
  - Graph tool-calling co ban dung retriever tool.
- `backend_ai/app/core/agent_graph_v2.py`
  - Ban v2, ve co ban giong `agent_graph.py` nhung duoc tach rieng de thu nghiem.
- `backend_ai/app/core/agent_graph_v3.py`
  - Graph nhieu node theo huong v3:
  - `classify -> retrieve -> answer -> escalate`
- `backend_ai/app/prompts/system_prompt.py`
  - Prompt cu cho graph tool-calling.
- `backend_ai/app/prompts/system_prompt_v3.py`
  - Prompt set moi cho v3, tach rieng cho `classify`, `answer`, `escalate`.
- `backend_ai/app/utils/retrieval_advanced.py`
  - Hybrid retriever:
  - BM25 + FAISS + RRF + Cross-Encoder reranker.
- `backend_ai/app/core/config.py`
  - Cau hinh duong dan toi `knowledge_base.sqlite`, `knowledge_base.faiss`, embedding model, LLM model.

### Frontend

- `frontend/web_demo/app.py`
  - Streamlit chat demo, goi `http://localhost:8000/chat`.

### Tai lieu va ha tang

- `docs/SYSTEM_ARCHITECTURE.md`
  - Mo ta kien truc tong quan muc tieu.
- `docs/API_CONTRACT.md`
  - Contract cu, can doi chieu lai voi `main_v3.py`.
- `.env.example`
  - Mau bien moi truong hien tai, van con dau vet Qdrant cu.
- `docker-compose.yml`
  - File compose cu, chua phan anh day du luong RAG v3 hien tai.

## 3. Trang thai hien tai / Known gaps

README nay huong theo `v3`, nhung repo hien tai chua dong bo hoan toan:

- `backend_ai/app/main_v3.py` da import dung `app.core.agent_graph_v3`, nhung o block `if __name__ == "__main__"` van goi `uvicorn.run("app.main:app", ...)` thay vi `app.main_v3:app`.
- `.env.example` van co bien Qdrant cu, trong khi luong retrieval hien tai dang dua tren `SQLite + FAISS`.
- `docs/API_CONTRACT.md` chua cap nhat theo response schema moi nhat cua `main_v3.py`.

Hieu ngan gon:

- `v3` la kien truc muc tieu va la chuan de tai lieu hoa.
- Runtime thuc te hien tai da noi vao `agent_graph_v3`, nhung van con mot vai dau vet cau hinh / tai lieu cu.

## 4. Setup moi truong

### Yeu cau

- Python 3.11+ khuyen nghi.
- Co `pip` va kha nang tai model Hugging Face.
- Co `OPENAI_API_KEY` hop le de goi LLM.

### Tao virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Cai dependencies

Backend:

```powershell
pip install -r backend_ai/requirements.txt
```

Data pipeline:

```powershell
pip install -r data_pipeline/requirements.txt
```

### Tao file moi truong

```powershell
Copy-Item .env.example .env
```

Bien toi thieu can co trong `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Luu y:

- `.env.example` hien con `QDRANT_URL` va `QDRANT_API_KEY`, nhung luong code retrieval hien tai khong dung Qdrant lam mac dinh.
- Cau hinh thuc te backend doc chu yeu tu `backend_ai/app/core/config.py`.

## 5. Data flow de nang cap RAG

Trinh tu mong muon de chay end-to-end:

1. Crawl / thu thap du lieu policy vao `data_pipeline/raw_data/`.
2. Chuan hoa du lieu thanh `data_pipeline/processed_data/chunks.jsonl`.
3. Chay `data_pipeline/db_setup/setup_db.py` de build:
   - `knowledge_base.sqlite`
   - `knowledge_base.faiss`
4. Khoi dong backend de load retriever.
5. Frontend goi `/chat` de gui cau hoi.

## 6. Runbook

### 6.1. Build knowledge base

Mac dinh `setup_db.py` doc:

- `data_pipeline/processed_data/chunks.jsonl`

Va sinh:

- `data_pipeline/db_setup/knowledge_base.sqlite`
- `data_pipeline/db_setup/knowledge_base.faiss`

Lenh chay:

```powershell
python data_pipeline/db_setup/setup_db.py
```

Neu can truyen tham so:

```powershell
python data_pipeline/db_setup/setup_db.py --chunks-file data_pipeline/processed_data/chunks.jsonl --sqlite-path data_pipeline/db_setup/knowledge_base.sqlite --faiss-path data_pipeline/db_setup/knowledge_base.faiss
```

### 6.2. Chay backend FastAPI

README nay coi `backend_ai/app/main_v3.py` la API tham chieu chinh.

Lenh chay:

```powershell
python backend_ai/app/main_v3.py
```

Hoac:

```powershell
uvicorn app.main_v3:app --host 0.0.0.0 --port 8000 --reload
```

Neu dung lenh `uvicorn`, chay trong thu muc `backend_ai`:

```powershell
cd backend_ai
uvicorn app.main_v3:app --host 0.0.0.0 --port 8000 --reload
```

### 6.3. Chay frontend Streamlit

```powershell
streamlit run frontend/web_demo/app.py
```

Frontend hien dang goi truc tiep:

- `POST http://localhost:8000/chat`

### 6.4. Health check nhanh

```powershell
curl http://localhost:8000/health
```

Response ky vong:

```json
{"status":"ok"}
```

### 6.5. Test nhanh `/chat`

```powershell
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Thuong huy chuyen nhu the nao?\",\"thread_id\":\"demo-thread-1\"}"
```

### 6.6. Test nhanh `/feedback`

```powershell
curl -X POST http://localhost:8000/feedback ^
  -H "Content-Type: application/json" ^
  -d "{\"thread_id\":\"demo-thread-1\",\"message_index\":0,\"reason\":\"wrong_case\",\"detail\":\"Tra loi chua dung ngu canh\"}"
```

## 7. API contract tham chieu theo `main_v3.py`

### `POST /chat`

Request:

```json
{
  "message": "string",
  "thread_id": "string"
}
```

`thread_id` co the de trong. Neu bo trong, backend se tu sinh UUID moi.

Response:

```json
{
  "reply": "string",
  "confidence": "high",
  "query_type": "policy",
  "escalate": false,
  "sources": [
    {
      "title": "string",
      "chunk_id": 123,
      "rerank_score": 0.91
    }
  ],
  "thread_id": "string"
}
```

Y nghia field:

- `confidence`: muc tin cay cua cau tra loi, du kien `high | low`.
- `query_type`: loai query do node classify xac dinh, du kien `policy | incident | general`.
- `escalate`: `true` khi frontend nen hien canh bao va dieu huong hotline.
- `sources`: metadata cua chunk da retrieve / rerank.

### `POST /feedback`

Request:

```json
{
  "thread_id": "string",
  "message_index": 0,
  "reason": "old_info",
  "detail": "string"
}
```

Response:

```json
{
  "status": "received",
  "message": "Cam on phan hoi cua ban. Chung toi se xem xet trong 24h."
}
```

## 8. Version notes

- `v1`
  - Skeleton / dummy response FastAPI.
- `v2`
  - LangGraph tool-calling co `thread_id` memory.
  - Retrieval dung retriever tool, chua tach classify / answer / escalate.
- `v3`
  - Graph tach node ro rang: `classify -> retrieve -> answer -> escalate`.
  - Response schema co `confidence`, `query_type`, `escalate`, `sources`.
  - Co them endpoint `POST /feedback`.

## 9. Huong nang cap tiep theo

- Sua block `uvicorn.run(...)` trong `backend_ai/app/main_v3.py` de tro dung `app.main_v3:app`.
- Chuan hoa `.env.example` theo luong `SQLite + FAISS`, bo giam phu thuoc Qdrant neu khong dung.
- Cap nhat `docs/API_CONTRACT.md` theo schema cua `main_v3.py`.
- Bo sung test va evaluation cho luong `v3`.

## 10. File can doc dau tien neu tiep tuc nang cap

Neu ban tiep tuc nang cap RAG, nen doc theo thu tu nay:

1. `backend_ai/app/main_v3.py`
2. `backend_ai/app/core/agent_graph_v3.py`
3. `backend_ai/app/prompts/system_prompt_v3.py`
4. `backend_ai/app/utils/retrieval_advanced.py`
5. `data_pipeline/db_setup/setup_db.py`
