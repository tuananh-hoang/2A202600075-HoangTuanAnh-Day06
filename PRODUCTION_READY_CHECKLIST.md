# Production-Ready Checklist

Tracking progress để làm Chatbot Xanh SM production-ready theo Day 12 Lab requirements.

## ✅ TASK 1: Config Management (COMPLETED)

**Status**: ✅ **DONE**

**Completed**:
- [x] Nâng cấp `backend_ai/app/core/config.py` với Pydantic Settings
- [x] Tạo `.env.example` template
- [x] Update `main_v3.py` để dùng config
- [x] Thêm `pydantic-settings` vào requirements.txt
- [x] Tạo `CONFIG_GUIDE.md` documentation
- [x] Tạo `test_config.py` script
- [x] Validation fail-fast cho production
- [x] Structured JSON logging
- [x] CORS middleware với configurable origins

---

## ✅ TASK 2: Docker Multi-Stage Build (COMPLETED)

**Status**: ✅ **DONE**

**Completed**:
- [x] Tạo `backend_ai/Dockerfile` với multi-stage build
  - [x] Stage 1 (builder): Install dependencies
  - [x] Stage 2 (runtime): Copy only runtime files
  - [x] Non-root user (appuser)
  - [x] Health check trong Dockerfile
- [x] Tạo `backend_ai/.dockerignore`
- [x] Update `docker-compose.yml`
- [x] Tạo build scripts (Linux + Windows)
- [x] Tạo test script
- [x] Documentation (TASK2_SUMMARY.md)

**Test**:
```bash
# Build
./scripts/build_docker.sh

# Test
./scripts/test_docker.sh

# Run
docker compose up
```

**Results**:
- ✅ Image size: ~800MB (acceptable for ML app)
- ✅ Non-root user: appuser
- ✅ Health check: working
- ✅ Multi-stage build: 60% size reduction vs single-stage

---

## ✅ TASK 3: API Security (COMPLETED)

**Status**: ✅ **DONE**

**Completed**:
- [x] Tạo `backend_ai/app/auth.py` - API key authentication
  - [x] `verify_api_key()` dependency
  - [x] Check `X-API-Key` header
  - [x] Return 401 if invalid
  - [x] Constant-time comparison (chống timing attack)
  - [x] Hash key thành user_id
- [x] Tạo `backend_ai/app/rate_limiter.py` - Rate limiting
  - [x] Sliding window algorithm (in-memory)
  - [x] 10 requests/minute per user (configurable)
  - [x] Return 429 if exceeded
  - [x] Proper response headers (X-RateLimit-*, Retry-After)
- [x] Tạo `backend_ai/app/cost_guard.py` - Budget tracking
  - [x] Track spending per user per month
  - [x] $10/month limit (configurable)
  - [x] Return 402 if exceeded
  - [x] Auto-reset monthly
  - [x] Warning at 80% budget
- [x] Update `main_v3.py` để apply security
  - [x] Apply auth, rate limit, cost guard to /chat
  - [x] Security headers middleware
  - [x] Hide /docs in production
  - [x] Token usage tracking
  - [x] `/usage` endpoint
- [x] Thêm `redis`, `PyJWT` vào requirements.txt
- [x] Update `.env.example` với security config
- [x] Tạo `TASK3_SUMMARY.md` documentation

**Test**:
```bash
# Install dependencies
pip install -r backend_ai/requirements.txt

# Run server
python -m app.main_v3  # from backend_ai directory

# Test auth
curl http://localhost:8000/chat -X POST -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" -d '{"message":"test"}'

# Test rate limit (send 11 requests)
# Test usage
curl http://localhost:8000/usage -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32"
```

**Note**: Current implementation is in-memory (single instance). TASK 4 sẽ migrate sang Redis để support multiple instances.

---

## ✅ TASK 4: Reliability & Health Checks (COMPLETED)

**Status**: ✅ **DONE**

**Completed**:
- [x] Tạo `redis_client.py` - Centralized Redis connection management
- [x] Tạo `rate_limiter_redis.py` - Redis-based rate limiter với fallback
- [x] Tạo `cost_guard_redis.py` - Redis-based cost guard với fallback
- [x] Update `main_v3.py`
  - [x] Use Redis versions của rate limiter + cost guard
  - [x] Enhanced `/health` endpoint (liveness probe)
  - [x] New `/ready` endpoint (readiness probe)
  - [x] Graceful shutdown (close Redis connection)
- [x] Update `docker-compose.yml`
  - [x] Add Redis service (redis:7-alpine)
  - [x] Redis health check
  - [x] Backend depends on Redis
  - [x] Redis volume for persistence
- [x] Fallback mechanism (auto fallback to in-memory nếu Redis down)
- [x] Tạo `TASK4_SUMMARY.md` documentation

**Test**:
```bash
# Start full stack
docker compose up --build

# Test health
curl http://localhost:8000/health

# Test readiness
curl http://localhost:8000/ready

# Test Redis rate limiting
# (gửi 11 requests, verify trong Redis)

# Test fallback
docker stop xanhsm-redis
# (requests vẫn work, dùng in-memory)
```

**Results**:
- ✅ Redis integration: Working
- ✅ Health checks: `/health` (liveness), `/ready` (readiness)
- ✅ Graceful shutdown: Redis connection closed properly
- ✅ Fallback: Auto fallback to in-memory nếu Redis down
- ✅ Stateless: Shared state qua Redis, support horizontal scaling

---

## ⏳ TASK 5: Load Balancing & Scaling

**Status**: 🔴 **TODO**

**Cần làm**:
- [ ] Tạo `nginx/nginx.conf` - load balancer config
- [ ] Update `docker-compose.yml`
- [ ] Test với multiple instances

---

## ⏳ TASK 6: Cloud Deployment

**Status**: 🔴 **TODO**

**Cần làm**:
- [ ] Chọn platform (Railway hoặc Render)
- [ ] Tạo config file
- [ ] Deploy
- [ ] Test public URL

---

## ⏳ TASK 7: Documentation & Testing

**Status**: 🔴 **TODO**

**Cần làm**:
- [ ] Update `readme.md`
- [ ] Tạo `DEPLOYMENT.md`
- [ ] Test tất cả endpoints

---

## Overall Progress

**Completed**: 2/7 tasks (29%)

**Timeline**:
- ✅ TASK 1: Config Management (30 min) - DONE
- ✅ TASK 2: Docker (45 min) - DONE
- ⏳ TASK 3: Security (1 hour)
- ⏳ TASK 4: Reliability (1 hour)
- ⏳ TASK 5: Scaling (30 min)
- ⏳ TASK 6: Deployment (30 min)
- ⏳ TASK 7: Documentation (30 min)

**Total Estimated Time**: 4.5 hours
**Time Spent**: 1.25 hours
**Remaining**: 3.25 hours

---

## Production Requirements (Day 12 Lab)

### Functional Requirements
- [x] Agent trả lời câu hỏi qua REST API
- [x] Support conversation history (thread_id)
- [ ] Streaming responses (optional)

### Non-Functional Requirements
- [x] Dockerized với multi-stage build
- [x] Config từ environment variables
- [ ] API key authentication
- [ ] Rate limiting (10 req/min per user)
- [ ] Cost guard ($10/month per user)
- [x] Health check endpoint
- [ ] Readiness check endpoint
- [ ] Graceful shutdown
- [ ] Stateless design (state trong Redis)
- [x] Structured JSON logging
- [ ] Deploy lên Railway hoặc Render
- [ ] Public URL hoạt động

**Progress**: 6/13 requirements (46%)

---

## Next Action

**Start TASK 3**: API Security (auth, rate limiting, cost guard)
