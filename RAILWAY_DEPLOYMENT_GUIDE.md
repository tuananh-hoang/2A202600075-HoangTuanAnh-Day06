# Railway Deployment Guide - Chatbot Xanh SM

## Prerequisites

1. **Railway Account**: Đăng ký tại [railway.app](https://railway.app)
2. **GitHub Repository**: Push code lên GitHub
3. **Railway CLI** (optional): `npm install -g @railway/cli`

---

## Option 1: Deploy via Railway Dashboard (RECOMMENDED)

### Step 1: Tạo Project Mới

1. Đăng nhập [railway.app](https://railway.app)
2. Click **"New Project"**
3. Chọn **"Deploy from GitHub repo"**
4. Authorize Railway access GitHub
5. Chọn repository: `NhomA1-C401-Day06`

### Step 2: Configure Build Settings

Railway sẽ tự động detect `railway.toml` và `Dockerfile`.

**Verify settings**:
- **Root Directory**: `/` (hoặc để trống)
- **Dockerfile Path**: `backend_ai/Dockerfile`
- **Build Command**: Auto-detected
- **Start Command**: `uvicorn app.main_v3:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Redis Database

1. Trong project dashboard, click **"New"** → **"Database"** → **"Add Redis"**
2. Railway sẽ tự động tạo Redis instance
3. Copy `REDIS_URL` từ Redis service (Railway tự động inject vào backend)

### Step 4: Configure Environment Variables

Click vào backend service → **"Variables"** tab:

```bash
# Required
OPENAI_API_KEY=sk-proj-...
AGENT_API_KEY=xanhsm-prod-key-2026-secure-random-string

# App Config
APP_NAME=Chatbot Tài Xế Xanh SM
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# Server (Railway auto-provides PORT)
HOST=0.0.0.0
# PORT is auto-injected by Railway

# LLM Config
LLM_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.0
MAX_TOKENS=500

# Embedding
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RETRIEVAL_TOP_K=5
RERANK_TOP_K=5

# Security
ALLOWED_ORIGINS=*
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=10
COST_GUARD_ENABLED=true
MONTHLY_BUDGET_USD=10.0

# Redis (auto-injected by Railway if you added Redis service)
# REDIS_URL=redis://...  (Railway provides this)
REDIS_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**CRITICAL**: 
- `OPENAI_API_KEY` - Thay bằng key thật
- `AGENT_API_KEY` - Generate secure random string (dùng cho production)

### Step 5: Upload Knowledge Base

**Problem**: Railway không có persistent storage cho files.

**Solutions**:

#### Option A: Bake into Docker image (RECOMMENDED for small KB)
```dockerfile
# In Dockerfile, copy knowledge base
COPY data_pipeline/db_setup /app/data_pipeline/db_setup
```

**Pros**: Đơn giản, không cần external storage
**Cons**: Rebuild image khi update KB

#### Option B: Use Railway Volume (Beta feature)
1. Railway dashboard → Service → **"Volumes"**
2. Mount path: `/app/data_pipeline/db_setup`
3. Upload files via Railway CLI

#### Option C: Use S3/Cloud Storage
1. Upload KB to S3
2. Download at startup trong `lifespan`
3. Cache locally

**For Day 12 Lab**: Dùng Option A (bake into image)

### Step 6: Deploy

1. Click **"Deploy"** button
2. Railway sẽ:
   - Clone repo
   - Build Docker image từ `backend_ai/Dockerfile`
   - Start container với environment variables
   - Expose public URL

**Build time**: ~5-10 phút (first deploy)

### Step 7: Verify Deployment

Railway sẽ cung cấp public URL: `https://your-app.up.railway.app`

**Test endpoints**:

```bash
# Health check
curl https://your-app.up.railway.app/health

# Readiness check
curl https://your-app.up.railway.app/ready

# Chat (với API key)
curl https://your-app.up.railway.app/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: xanhsm-prod-key-2026-secure-random-string" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'
```

### Step 8: Monitor

Railway dashboard cung cấp:
- **Logs**: Real-time logs (JSON format)
- **Metrics**: CPU, Memory, Network usage
- **Deployments**: History, rollback
- **Health checks**: Status của `/health` endpoint

---

## Option 2: Deploy via Railway CLI

### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
```

### Step 2: Login

```bash
railway login
```

### Step 3: Initialize Project

```bash
cd NhomA1-C401-Day06
railway init
```

Chọn:
- **Create new project**: Yes
- **Project name**: chatbot-xanh-sm

### Step 4: Link to GitHub (Optional)

```bash
railway link
```

### Step 5: Add Redis

```bash
railway add --database redis
```

### Step 6: Set Environment Variables

```bash
# Set từ file
railway variables --set-from-file .env.production

# Hoặc set từng biến
railway variables set OPENAI_API_KEY=sk-proj-...
railway variables set AGENT_API_KEY=xanhsm-prod-key-2026-...
railway variables set ENVIRONMENT=production
railway variables set REDIS_ENABLED=true
```

### Step 7: Deploy

```bash
railway up
```

Railway sẽ:
1. Detect `railway.toml`
2. Build Docker image
3. Deploy to production

### Step 8: Get Public URL

```bash
railway domain
```

---

## Knowledge Base Deployment Strategy

### Strategy 1: Bake into Docker Image (RECOMMENDED)

Update `backend_ai/Dockerfile`:

```dockerfile
# After COPY app/ /app/app/
COPY data_pipeline/db_setup /app/data_pipeline/db_setup
```

**Pros**:
- ✅ Đơn giản
- ✅ Không cần external storage
- ✅ Fast startup

**Cons**:
- ❌ Rebuild image khi update KB
- ❌ Tăng image size (~100-200MB)

### Strategy 2: Download from S3 at Startup

Update `main_v3.py` lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Download KB from S3
    if settings.environment == "production":
        import boto3
        s3 = boto3.client('s3')
        s3.download_file('my-bucket', 'knowledge_base.sqlite', '/app/data/knowledge_base.sqlite')
        s3.download_file('my-bucket', 'knowledge_base.faiss', '/app/data/knowledge_base.faiss')
    
    # Load RAG agent
    ...
```

**Pros**:
- ✅ Update KB without rebuild
- ✅ Smaller image size

**Cons**:
- ❌ Slower startup (~10-30s)
- ❌ Need S3 credentials
- ❌ More complex

### Strategy 3: Railway Volume (Beta)

```bash
railway volume create kb-data
railway volume mount kb-data /app/data_pipeline/db_setup
```

Upload files:
```bash
railway volume upload kb-data ./data_pipeline/db_setup/
```

**Pros**:
- ✅ Persistent storage
- ✅ Update without rebuild

**Cons**:
- ❌ Beta feature (có thể unstable)
- ❌ Manual upload

**For Day 12 Lab**: Dùng Strategy 1 (bake into image)

---

## Scaling on Railway

### Horizontal Scaling

Railway dashboard → Service → **"Settings"** → **"Replicas"**

Set replicas: 1 → 3

**Requirements**:
- ✅ Redis enabled (shared state)
- ✅ Stateless design (no local files)
- ✅ Health checks configured

Railway sẽ:
- Load balance traffic giữa replicas
- Auto-restart unhealthy replicas
- Share Redis connection

### Vertical Scaling

Railway dashboard → Service → **"Settings"** → **"Resources"**

Adjust:
- **CPU**: 0.5 vCPU → 2 vCPU
- **Memory**: 512MB → 2GB

**Recommendations**:
- Development: 0.5 vCPU, 512MB
- Production: 1 vCPU, 1GB
- High traffic: 2 vCPU, 2GB

---

## Cost Estimation

### Railway Pricing (as of 2024)

**Free Tier**:
- $5 credit/month
- Enough for development/testing

**Pro Plan** ($20/month):
- $20 credit included
- $0.000231/GB-hour (memory)
- $0.000463/vCPU-hour

**Estimated costs**:

| Configuration | Monthly Cost |
|---------------|--------------|
| 1 replica, 512MB, 0.5 vCPU | ~$8-10 |
| 1 replica, 1GB, 1 vCPU | ~$15-20 |
| 3 replicas, 1GB, 1 vCPU | ~$45-60 |

**Redis addon**: ~$5-10/month

**Total for Day 12 Lab**: ~$15-20/month (1 backend + Redis)

---

## Troubleshooting

### Issue 1: Build Failed

**Error**: `No module named 'app'`

**Fix**: Verify `railway.toml` has correct `dockerfilePath`:
```toml
dockerfilePath = "backend_ai/Dockerfile"
```

### Issue 2: Health Check Failed

**Error**: Container keeps restarting

**Fix**: 
1. Check logs: Railway dashboard → **"Logs"**
2. Verify `/health` endpoint returns 200
3. Increase `healthcheckTimeout` in `railway.toml`

### Issue 3: Redis Connection Failed

**Error**: `Redis connection failed`

**Fix**:
1. Verify Redis service is running
2. Check `REDIS_URL` environment variable
3. Set `REDIS_ENABLED=true`

### Issue 4: Knowledge Base Not Found

**Error**: `FileNotFoundError: knowledge_base.sqlite`

**Fix**:
1. Verify KB files are in Docker image:
   ```dockerfile
   COPY data_pipeline/db_setup /app/data_pipeline/db_setup
   ```
2. Check paths in `config.py`

### Issue 5: Port Binding Error

**Error**: `Address already in use`

**Fix**: Railway provides `$PORT` dynamically. Dockerfile should use:
```dockerfile
CMD ["sh", "-c", "uvicorn app.main_v3:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

---

## Security Checklist

Before deploying to production:

- [ ] Change `AGENT_API_KEY` to secure random string
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Verify `ALLOWED_ORIGINS` (không dùng `*` trong production)
- [ ] Enable `RATE_LIMIT_ENABLED=true`
- [ ] Enable `COST_GUARD_ENABLED=true`
- [ ] Set `LOG_FORMAT=json`
- [ ] Verify `OPENAI_API_KEY` is valid
- [ ] Test `/health` and `/ready` endpoints
- [ ] Test authentication với API key
- [ ] Test rate limiting
- [ ] Monitor logs for errors

---

## Post-Deployment

### 1. Update Frontend

Nếu có Streamlit frontend, update `BACKEND_URL`:

```bash
# .env for frontend
BACKEND_URL=https://your-app.up.railway.app/chat
```

Deploy frontend separately hoặc update local frontend.

### 2. Test Full Flow

```bash
# Test chat
curl https://your-app.up.railway.app/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-prod-key" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'

# Test rate limiting (11 requests)
for i in {1..11}; do
  curl https://your-app.up.railway.app/chat -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-prod-key" \
    -d '{"message":"test"}' \
    -w "\nHTTP: %{http_code}\n"
done

# Test usage
curl https://your-app.up.railway.app/usage \
  -H "X-API-Key: your-prod-key"
```

### 3. Monitor

Railway dashboard:
- **Logs**: Check for errors
- **Metrics**: CPU, Memory usage
- **Health**: Verify `/health` is green

### 4. Document Public URL

Save public URL for submission:
```
https://chatbot-xanh-sm-production.up.railway.app
```

---

## Rollback

Nếu deployment có vấn đề:

1. Railway dashboard → **"Deployments"**
2. Find previous working deployment
3. Click **"Redeploy"**

Hoặc via CLI:
```bash
railway rollback
```

---

## References

- [Railway Documentation](https://docs.railway.app/)
- [Railway Dockerfile Guide](https://docs.railway.app/deploy/dockerfiles)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)
- [Railway Redis](https://docs.railway.app/databases/redis)
- [Railway CLI](https://docs.railway.app/develop/cli)
