# Hướng Dẫn Deploy - Chatbot Xanh SM

## Thông Tin Deployment

**Platform**: Railway  
**Repository**: https://github.com/tuananh-hoang/2A202600075-HoangTuanAnh-Day06  
**Public URL**: https://2a202600075-hoangtuananh-day06-production.up.railway.app  
**Deploy Status**: ✅ Deployment successful!

---

## Kiến Trúc Hệ Thống

### Services
1. **Backend API** (FastAPI)
   - Port: 8000 (Railway tự động assign)
   - Framework: FastAPI + LangChain + LangGraph
   - Python: 3.11
   - Docker: Multi-stage build

2. **Redis** (Database)
   - Port: 6379
   - Chức năng: Rate limiting, Cost guard, Session storage
   - Managed by Railway

3. **Qdrant** (Vector Database)
   - Không deploy (chỉ dùng local development)
   - Production: Dùng FAISS embedded trong container

### Tech Stack
- **Backend**: FastAPI, Uvicorn
- **AI/LLM**: OpenAI GPT-4o-mini, LangChain, LangGraph
- **RAG**: FAISS, Sentence Transformers, BM25, CrossEncoder
- **Security**: API Key auth, Rate limiting, Cost guard
- **Database**: Redis (state), SQLite (knowledge base), FAISS (vector search)
- **Deployment**: Docker, Railway

---

## Cấu Trúc Project

```
NhomA1-C401-Day06/
├── backend_ai/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings
│   │   │   ├── agent_graph_v4.py  # LangGraph workflow
│   │   ├── auth.py                # API key authentication
│   │   ├── rate_limiter_redis.py  # Redis rate limiter
│   │   ├── cost_guard_redis.py    # Budget tracking
│   │   ├── redis_client.py        # Redis connection
│   │   └── main_v3.py             # FastAPI app
│   ├── Dockerfile                 # Local development
│   ├── Dockerfile.railway         # Railway production
│   └── requirements.txt
├── data_pipeline/
│   └── db_setup/
│       ├── knowledge_base.sqlite  # Knowledge base
│       └── knowledge_base.faiss   # Vector embeddings
├── railway.toml                   # Railway config
├── docker-compose.yml             # Local development
└── .env.example                   # Environment template
```

---

## Prerequisites

### 1. Tài Khoản & Services
- [x] GitHub account
- [x] Railway account (https://railway.app)
- [x] OpenAI API key

### 2. Local Development
- Python 3.11+
- Docker & Docker Compose
- Git

---

## Bước 1: Chuẩn Bị Code

### 1.1. Clone Repository

```bash
git clone https://github.com/tuananh-hoang/2A202600075-HoangTuanAnh-Day06.git
cd 2A202600075-HoangTuanAnh-Day06
```

### 1.2. Cấu Trúc Files Quan Trọng

**Railway Config** (`railway.toml`):
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend_ai/Dockerfile.railway"
watchPatterns = ["backend_ai/**", "data_pipeline/**"]

[deploy]
startCommand = "uvicorn app.main_v3:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

**Dockerfile** (`backend_ai/Dockerfile.railway`):
- Multi-stage build (builder + runtime)
- Non-root user (appuser)
- Health check enabled
- Knowledge base baked into image

---

## Bước 2: Deploy Lên Railway

### 2.1. Tạo Project Từ GitHub

1. Đăng nhập Railway: https://railway.app
2. Click **"New Project"**
3. Chọn **"Deploy from GitHub repo"**
4. Authorize Railway access GitHub
5. Chọn repository: `2A202600075-HoangTuanAnh-Day06`

Railway sẽ tự động:
- Detect `railway.toml`
- Detect `backend_ai/Dockerfile.railway`
- Bắt đầu build

### 2.2. Add Redis Database

1. Trong project dashboard, click **"New"**
2. Chọn **"Database"** → **"Add Redis"**
3. Railway tự động tạo Redis và inject `REDIS_URL`

### 2.3. Configure Environment Variables

Click vào backend service → Tab **"Variables"** → **"RAW Editor"**

Copy-paste config sau (thay `YOUR_OPENAI_KEY` và `YOUR_API_KEY`):

```bash
HOST=0.0.0.0
ENVIRONMENT=production
DEBUG=false
APP_NAME=Chatbot Tài Xế Xanh SM
APP_VERSION=1.0.0

# CRITICAL: Thay bằng key thật
OPENAI_API_KEY=sk-proj-YOUR-REAL-KEY-HERE
AGENT_API_KEY=YOUR-SECURE-RANDOM-STRING

LLM_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.0
MAX_TOKENS=500

EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RETRIEVAL_TOP_K=5
RERANK_TOP_K=5

ALLOWED_ORIGINS=*
REDIS_ENABLED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=10
COST_GUARD_ENABLED=true
MONTHLY_BUDGET_USD=10.0

LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Generate secure API key**:
```powershell
# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

### 2.4. Deploy

Railway sẽ tự động trigger deployment sau khi set variables.

**Monitor deployment**:
1. Click vào backend service
2. Tab **"Deployments"**
3. Xem build logs

**Build time**: ~5-10 phút (first deploy)

### 2.5. Generate Public URL

1. Backend service → Tab **"Settings"**
2. Scroll xuống **"Networking"** → **"Public Networking"**
3. Click **"Generate Domain"**

Railway sẽ tạo URL: `https://[app-name].up.railway.app`

---

## Bước 3: Verify Deployment

### 3.1. Health Check

```bash
curl https://[your-app].up.railway.app/health
```

**Expected**:
```json
{
  "status": "ok",
  "app": "Chatbot Tài Xế Xanh SM",
  "version": "1.0.0",
  "environment": "production"
}
```

### 3.2. Readiness Check

```bash
curl https://[your-app].up.railway.app/ready
```

**Expected**:
```json
{
  "status": "ready",
  "checks": {
    "redis": "ok",
    "rag_agent": "ok"
  }
}
```

### 3.3. Test Chat Endpoint

```bash
curl https://[your-app].up.railway.app/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR-API-KEY" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'
```

**Expected**: Response với `reply`, `confidence`, `sources`, `thread_id`

### 3.4. Test Rate Limiting

```bash
# Gửi 11 requests liên tiếp
for i in {1..11}; do
  curl https://[your-app].up.railway.app/chat -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: YOUR-API-KEY" \
    -d '{"message":"test"}' \
    -w "\nHTTP: %{http_code}\n"
done
```

**Expected**: Request thứ 11 nhận `429 Too Many Requests`

### 3.5. Test Usage Endpoint

```bash
curl https://[your-app].up.railway.app/usage \
  -H "X-API-Key: YOUR-API-KEY"
```

**Expected**: Thông tin về cost, rate limit, tokens used

---

## Bước 4: Monitor & Maintain

### 4.1. View Logs

Railway dashboard → Backend service → Tab **"Logs"**

**Logs format**: Structured JSON
```json
{"time":"2026-04-17 ...","level":"INFO","msg":"..."}
```

### 4.2. Monitor Metrics

Railway dashboard → Backend service → Tab **"Metrics"**

**Metrics**:
- CPU usage
- Memory usage
- Network traffic
- Request count

### 4.3. Check Deployment History

Railway dashboard → Backend service → Tab **"Deployments"**

**Actions**:
- View previous deployments
- Rollback to previous version
- Redeploy

---

## Production Features

### ✅ Config Management (12-Factor App)
- Environment variables từ Railway
- Pydantic Settings validation
- Fail-fast cho production

### ✅ Docker Multi-Stage Build
- Builder stage: Install dependencies
- Runtime stage: Minimal image (~800MB)
- Non-root user (appuser)
- Health check enabled

### ✅ API Security
- **Authentication**: API key via `X-API-Key` header
- **Rate Limiting**: 10 requests/minute per user (Redis-based)
- **Cost Guard**: $10/month budget per user
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, etc.

### ✅ Reliability & Health Checks
- **Liveness probe**: `/health` endpoint
- **Readiness probe**: `/ready` endpoint (check Redis + RAG agent)
- **Graceful shutdown**: Close connections properly
- **Stateless design**: All state in Redis

### ✅ Observability
- **Structured logging**: JSON format
- **Request tracking**: thread_id, user_id
- **Error logging**: Detailed error messages
- **Usage tracking**: Tokens, cost, rate limit stats

---

## Troubleshooting

### Issue 1: Build Failed

**Error**: `failed to build: failed to solve`

**Check**:
1. Railway dashboard → Deployments → View logs
2. Verify `railway.toml` config
3. Check Dockerfile syntax

**Fix**:
```bash
# Trigger redeploy
git commit --allow-empty -m "Trigger redeploy"
git push origin main
```

### Issue 2: Container Keeps Restarting

**Error**: Container restart loop

**Check**:
1. Railway → Logs → Search for errors
2. Verify environment variables
3. Check `/health` endpoint

**Common causes**:
- Missing `OPENAI_API_KEY`
- Redis connection failed
- Knowledge base files not found

**Fix**: Update environment variables trong Railway dashboard

### Issue 3: 502 Bad Gateway

**Cause**: Container chưa ready

**Fix**: Đợi 1-2 phút, Railway đang start container

### Issue 4: Rate Limit Not Working

**Check**:
1. Verify `REDIS_ENABLED=true`
2. Check Redis service is running
3. View logs: Search "Redis"

**Fix**: Restart Redis service hoặc backend service

---

## Scaling

### Horizontal Scaling

Railway dashboard → Backend service → **"Settings"** → **"Replicas"**

Set replicas: 1 → 3

**Requirements**:
- ✅ Redis enabled (shared state)
- ✅ Stateless design
- ✅ Health checks configured

### Vertical Scaling

Railway dashboard → Backend service → **"Settings"** → **"Resources"**

**Recommendations**:
- Development: 0.5 vCPU, 512MB
- Production: 1 vCPU, 1GB
- High traffic: 2 vCPU, 2GB

---

## Cost Estimation

### Railway Pricing

**Free Tier**: $5 credit/month (đủ cho testing)

**Pro Plan**: $20/month
- $20 credit included
- $0.000231/GB-hour (memory)
- $0.000463/vCPU-hour

**Estimated Monthly Cost**:
- 1 backend instance (1GB, 1 vCPU): ~$15
- Redis addon: ~$5
- **Total**: ~$20/month

---

## Security Checklist

- [x] API key authentication enabled
- [x] Rate limiting enabled (10 req/min)
- [x] Cost guard enabled ($10/month)
- [x] Security headers configured
- [x] HTTPS enabled (Railway default)
- [x] Environment variables secured
- [x] Logs không chứa secrets
- [x] Non-root user trong container
- [x] Health checks configured

---

## Rollback

Nếu deployment có vấn đề:

1. Railway dashboard → **"Deployments"**
2. Find previous working deployment
3. Click **"Redeploy"**

Hoặc via Git:
```bash
git revert HEAD
git push origin main
```

---

## Support & Documentation

### Project Documentation
- `README.md` - Project overview
- `CONFIG_GUIDE.md` - Configuration reference
- `TASK1_SUMMARY.md` - Config management
- `TASK2_SUMMARY.md` - Docker setup
- `TASK3_SUMMARY.md` - API security
- `TASK4_SUMMARY.md` - Reliability & health checks
- `RAILWAY_DEPLOYMENT_GUIDE.md` - Detailed deployment guide

### External Resources
- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

## Thông Tin Liên Hệ

**Sinh viên**: Hoàng Tuấn Anh  
**MSSV**: 2A202600075  
**Lớp**: C401  
**Project**: Chatbot Xanh SM - Day 12 Lab  
**Repository**: https://github.com/tuananh-hoang/2A202600075-HoangTuanAnh-Day06

---

## Changelog

### Version 1.0.0 (2026-04-17)
- ✅ Initial production deployment
- ✅ Config management với Pydantic Settings
- ✅ Docker multi-stage build
- ✅ API security (auth + rate limiting + cost guard)
- ✅ Redis integration
- ✅ Health checks (`/health`, `/ready`)
- ✅ Graceful shutdown
- ✅ Railway deployment

---

**Last Updated**: 2026-04-17  
**Status**: ✅ Production Ready
