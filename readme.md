# Chatbot Xanh SM - Production Deployment (Day 12 Lab)

> **AICB-P1 · VinUniversity 2026**  
> **Sinh viên**: Hoàng Tuấn Anh  
> **MSSV**: 2A202600075  
> **Lớp**: C401  
> **Project**: Production-Ready AI Chatbot Deployment

---

## 📋 Tổng Quan

Dự án này là phần triển khai production-ready cho **Chatbot Tài Xế Xanh SM** - một hệ thống RAG (Retrieval-Augmented Generation) hỗ trợ tài xế tra cứu chính sách, điều khoản và quy trình xử lý sự cố.

**Mục tiêu Day 12 Lab**: Chuyển đổi prototype thành production-ready system với:
- ✅ Docker containerization
- ✅ Cloud deployment (Railway)
- ✅ API security (authentication + rate limiting)
- ✅ Health checks & reliability
- ✅ 12-Factor App principles

---

## 🏗️ Kiến Trúc Hệ Thống

### Tech Stack

**Backend**:
- FastAPI + Uvicorn
- LangChain + LangGraph (Agent workflow)
- OpenAI GPT-4o-mini

**RAG Pipeline**:
- FAISS (vector search)
- BM25 (sparse search)
- Sentence Transformers (embedding)
- Cross-encoder (reranking)
- SQLite (knowledge base)

**Infrastructure**:
- Docker (multi-stage build)
- Railway (cloud platform)
- Redis (rate limiting & state management - optional)

### Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Railway Platform   │
│  ┌───────────────┐  │
│  │  FastAPI App  │  │
│  │  (Container)  │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │  Knowledge    │  │
│  │  Base (FAISS) │  │
│  └───────────────┘  │
└─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- OpenAI API key (optional - có mock LLM)

### 1. Clone Repository

```bash
git clone https://github.com/tuananh-hoang/2A202600075-HoangTuanAnh-Day06.git
cd 2A202600075-HoangTuanAnh-Day06
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env và thêm API keys
# AGENT_API_KEY=your-secure-key-here
# OPENAI_API_KEY=sk-proj-... (optional)
```

### 3. Run Locally với Docker

```bash
# Build và run
docker compose up --build

# Hoặc chỉ backend
cd backend_ai
docker build -t chatbot-backend .
docker run -p 8000:8000 --env-file ../.env chatbot-backend
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint (cần API key)
curl http://localhost:8000/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'
```

---

## 📦 Production Deployment

### Deploy to Railway

**Public URL**: `https://[your-app].up.railway.app` (sẽ cập nhật sau khi deploy)

#### Bước 1: Push Code lên GitHub

```bash
git add .
git commit -m "Production-ready deployment"
git push origin main
```

#### Bước 2: Tạo Project trên Railway

1. Truy cập https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Chọn repository: `2A202600075-HoangTuanAnh-Day06`
4. Railway tự động detect `railway.toml` và `Dockerfile.railway`

#### Bước 3: Set Environment Variables

Railway dashboard → Backend service → Tab "Variables" → RAW Editor:

```bash
HOST=0.0.0.0
ENVIRONMENT=production
DEBUG=false
APP_NAME=Chatbot Tài Xế Xanh SM
APP_VERSION=1.0.0

# CRITICAL: Thay bằng key thật
AGENT_API_KEY=xanhsm-prod-railway-2026-abc123
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE

LLM_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.0
MAX_TOKENS=500

EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RETRIEVAL_TOP_K=5
RERANK_TOP_K=5

ALLOWED_ORIGINS=*
REDIS_ENABLED=false
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=10
COST_GUARD_ENABLED=false
MONTHLY_BUDGET_USD=10.0

LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Bước 4: Generate Public URL

Railway dashboard → Backend service → Settings → Networking → "Generate Domain"

#### Bước 5: Verify Deployment

```bash
# Health check
curl https://[your-app].up.railway.app/health

# Readiness check
curl https://[your-app].up.railway.app/ready

# Test chat
curl https://[your-app].up.railway.app/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR-API-KEY" \
  -d '{"message":"test"}'
```

---

## 🔒 Production Features

### ✅ Config Management (12-Factor App)

- **Environment variables**: Tất cả config từ env vars, không hardcode
- **Pydantic Settings**: Type-safe validation
- **Fail-fast**: Validation lỗi ngay khi start nếu thiếu config quan trọng

**File**: `backend_ai/app/core/config.py`

### ✅ Docker Multi-Stage Build

- **Stage 1 (builder)**: Install dependencies với build tools
- **Stage 2 (runtime)**: Copy chỉ runtime files, minimal image
- **Non-root user**: Container chạy với user `appuser` (UID 1000)
- **Health check**: Built-in health check endpoint

**File**: `backend_ai/Dockerfile.railway`

**Image size**: ~800MB (acceptable cho ML app với FAISS + transformers)

### ✅ API Security

#### Authentication
- **API Key**: Via `X-API-Key` header
- **Constant-time comparison**: Tránh timing attacks

**File**: `backend_ai/app/auth.py`

#### Rate Limiting
- **Algorithm**: Sliding window
- **Default**: 10 requests/minute per user
- **Storage**: In-memory (có thể upgrade lên Redis)

**File**: `backend_ai/app/rate_limiter.py`

#### Cost Guard
- **Budget**: $10/month per user
- **Tracking**: Token usage estimation
- **Storage**: In-memory (có thể upgrade lên Redis)

**File**: `backend_ai/app/cost_guard.py`

### ✅ Reliability & Health Checks

#### Liveness Probe
```bash
GET /health
```
Kiểm tra container còn sống không.

#### Readiness Probe
```bash
GET /ready
```
Kiểm tra app sẵn sàng nhận traffic (check Redis, RAG agent).

#### Graceful Shutdown
- Handle SIGTERM signal
- Finish current requests
- Close connections properly

**File**: `backend_ai/app/main_v3.py`

### ✅ Observability

- **Structured logging**: JSON format
- **Request tracking**: `thread_id` cho mỗi conversation
- **Error logging**: Detailed error messages
- **Usage tracking**: Tokens, cost, rate limit stats

---

## 📁 Project Structure

```
NhomA1-C401-Day06/
├── backend_ai/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic Settings
│   │   │   ├── agent_graph_v4.py      # LangGraph workflow
│   │   ├── prompts/
│   │   │   └── system_prompt_v4.py    # Agent prompts
│   │   ├── utils/
│   │   │   └── retrieval_advanced.py  # Hybrid RAG
│   │   ├── auth.py                    # API key auth
│   │   ├── rate_limiter.py            # Rate limiting
│   │   ├── cost_guard.py              # Budget tracking
│   │   ├── redis_client.py            # Redis connection
│   │   └── main_v3.py                 # FastAPI app
│   ├── Dockerfile                     # Local development
│   ├── Dockerfile.railway             # Railway production
│   ├── start.py                       # Railway startup script
│   └── requirements.txt
├── data_pipeline/
│   └── db_setup/
│       ├── knowledge_base.sqlite      # Knowledge base
│       └── knowledge_base.faiss       # Vector embeddings
├── frontend/
│   └── web_demo/
│       └── app.py                     # Streamlit UI
├── scripts/
│   ├── build_docker.sh                # Build script (Linux/Mac)
│   └── build_docker.ps1               # Build script (Windows)
├── railway.toml                       # Railway config
├── docker-compose.yml                 # Local development
├── .env.example                       # Environment template
├── .railwayignore                     # Railway ignore
├── README.md                          # This file
├── DEPLOY.md                          # Deployment guide
├── MISSION_ANSWERS.md                 # Lab answers
└── PRODUCTION_READY_CHECKLIST.md      # Production checklist
```

---

## 🧪 Testing

### Local Testing

```bash
# Start services
docker compose up

# Test health
curl http://localhost:8000/health

# Test chat (với auth)
curl http://localhost:8000/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'

# Test rate limiting (gửi 11 requests)
for i in {1..11}; do
  curl http://localhost:8000/chat -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
    -d '{"message":"test"}' \
    -w "\nHTTP: %{http_code}\n"
done
```

### Production Testing

```bash
# Replace [your-app] with actual Railway domain
export API_URL=https://[your-app].up.railway.app
export API_KEY=your-production-key

# Health check
curl $API_URL/health

# Readiness check
curl $API_URL/ready

# Chat test
curl $API_URL/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'

# Usage stats
curl $API_URL/usage -H "X-API-Key: $API_KEY"
```

---

## 📊 API Reference

### `POST /chat`

**Request**:
```json
{
  "message": "Điều khoản bảo hiểm là gì?",
  "thread_id": "optional-conversation-id"
}
```

**Response**:
```json
{
  "reply": "Điều khoản bảo hiểm bao gồm...",
  "confidence": "high",
  "query_type": "policy",
  "escalate": false,
  "sources": [
    {
      "title": "Chính sách bảo hiểm",
      "url": "https://...",
      "chunk_id": 123,
      "rerank_score": 0.91
    }
  ],
  "thread_id": "abc-123-def"
}
```

### `GET /health`

**Response**:
```json
{
  "status": "ok",
  "app": "Chatbot Tài Xế Xanh SM",
  "version": "1.0.0",
  "environment": "production"
}
```

### `GET /ready`

**Response**:
```json
{
  "status": "ready",
  "checks": {
    "redis": "ok",
    "rag_agent": "ok"
  }
}
```

### `GET /usage`

**Headers**: `X-API-Key: your-key`

**Response**:
```json
{
  "user_id": "user-123",
  "rate_limit": {
    "remaining": 8,
    "limit": 10,
    "reset_at": "2026-04-17T12:00:00Z"
  },
  "cost_guard": {
    "used": 2.5,
    "budget": 10.0,
    "currency": "USD"
  }
}
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port (Railway auto-assigns) |
| `ENVIRONMENT` | No | `development` | `development` \| `production` |
| `DEBUG` | No | `false` | Debug mode |
| `AGENT_API_KEY` | **Yes** (prod) | - | API key for authentication |
| `OPENAI_API_KEY` | No | - | OpenAI API key (uses mock if not set) |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model |
| `RATE_LIMIT_ENABLED` | No | `false` | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | No | `10` | Requests per minute |
| `COST_GUARD_ENABLED` | No | `false` | Enable cost guard |
| `MONTHLY_BUDGET_USD` | No | `10.0` | Monthly budget per user |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FORMAT` | No | `json` | `json` \| `text` |

**Xem thêm**: `CONFIG_GUIDE.md`

---

## 📚 Documentation

- **[DEPLOY.md](DEPLOY.md)** - Hướng dẫn deploy chi tiết
- **[MISSION_ANSWERS.md](MISSION_ANSWERS.md)** - Câu trả lời lab exercises
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Configuration reference
- **[PRODUCTION_READY_CHECKLIST.md](PRODUCTION_READY_CHECKLIST.md)** - Production checklist
- **[TASK1_SUMMARY.md](TASK1_SUMMARY.md)** - Config management summary
- **[TASK2_SUMMARY.md](TASK2_SUMMARY.md)** - Docker setup summary
- **[TASK3_SUMMARY.md](TASK3_SUMMARY.md)** - API security summary
- **[TASK4_SUMMARY.md](TASK4_SUMMARY.md)** - Reliability summary

---

## 🐛 Troubleshooting

### Issue: Container fails to start

**Error**: `AGENT_API_KEY must be set in production!`

**Fix**: Set `AGENT_API_KEY` environment variable trong Railway dashboard.

### Issue: Knowledge base not found

**Error**: `SQLite DB not found: /app/data_pipeline/db_setup/knowledge_base.sqlite`

**Fix**: Knowledge base files đã được baked vào Docker image. Nếu vẫn lỗi, check Dockerfile COPY paths.

### Issue: Rate limit not working

**Fix**: Set `RATE_LIMIT_ENABLED=true` và `REDIS_ENABLED=true` (nếu dùng Redis).

**Xem thêm**: `DEPLOY.md` - Troubleshooting section

---

## 🎯 Production Checklist

- [x] Config từ environment variables
- [x] Docker multi-stage build
- [x] API key authentication
- [x] Rate limiting
- [x] Cost guard
- [x] Health checks (`/health`, `/ready`)
- [x] Graceful shutdown
- [x] Structured logging (JSON)
- [x] Non-root user trong container
- [x] Security headers
- [x] Deploy lên Railway
- [ ] Public URL hoạt động (đang deploy)
- [ ] Redis integration (optional)
- [ ] Monitoring & alerting (future)

---

## 📈 Performance

- **Response time**: ~2-3s (với OpenAI API)
- **Throughput**: ~10 req/min per user (rate limited)
- **Memory**: ~800MB (Docker image)
- **CPU**: 0.5-1 vCPU (Railway)

---

## 🔐 Security

- ✅ API key authentication
- ✅ Rate limiting (10 req/min)
- ✅ Cost guard ($10/month)
- ✅ HTTPS enabled (Railway default)
- ✅ Security headers configured
- ✅ No secrets in code
- ✅ Non-root container user
- ✅ Environment variable validation

---

## 📝 License

This project is for educational purposes (VinUniversity AICB-P1 Course).

---

## 👥 Team

**Sinh viên**: Hoàng Tuấn Anh  
**MSSV**: 2A202600075  
**Lớp**: C401  
**Project**: Chatbot Xanh SM - Day 12 Lab

---

## 🙏 Acknowledgments

- VinUniversity AICB-P1 Course
- OpenAI API
- LangChain & LangGraph
- Railway Platform
- FastAPI Framework

---

**Last Updated**: 2026-04-17  
**Status**: ✅ Production Ready (deploying to Railway)
