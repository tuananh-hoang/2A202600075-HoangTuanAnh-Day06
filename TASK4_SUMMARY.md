# TASK 4: Reliability & Health Checks - HOÀN THÀNH ✅

## Tổng Quan

Nâng cấp hệ thống để production-ready với:

1. **Redis Integration** - Migrate rate limiter + cost guard sang Redis
2. **Enhanced Health Checks** - `/health` (liveness) + `/ready` (readiness)
3. **Graceful Shutdown** - Đóng connections properly khi shutdown
4. **Stateless Design** - Shared state qua Redis, support horizontal scaling
5. **Fallback Mechanism** - Auto fallback về in-memory nếu Redis down

---

## Files Đã Tạo

### 1. `backend_ai/app/redis_client.py`
**Chức năng**: Centralized Redis connection management

- Singleton pattern với connection pooling
- Auto-reconnect với health check interval
- `get_client()` - Lấy Redis client instance
- `is_healthy()` - Check Redis connection health
- `close()` - Graceful shutdown

**Features**:
- Connection timeout: 5s
- Health check interval: 30s
- Retry on timeout
- Auto decode bytes to string

### 2. `backend_ai/app/rate_limiter_redis.py`
**Chức năng**: Redis-based sliding window rate limiter

**Algorithm**: Redis Sorted Set (ZSET)
- Key: `rate_limit:{user_id}`
- Score: timestamp
- Member: request_id
- TTL: window_seconds + 10s buffer

**Operations** (atomic via pipeline):
1. `ZREMRANGEBYSCORE` - Xóa timestamps cũ
2. `ZCARD` - Đếm requests trong window
3. `ZADD` - Thêm request mới
4. `EXPIRE` - Set TTL

**Fallback**: Auto fallback về in-memory limiter nếu Redis down

### 3. `backend_ai/app/cost_guard_redis.py`
**Chức năng**: Redis-based monthly budget guard

**Data Structure**:
- Key: `cost_guard:{user_id}:{month}`
- Value: JSON `{input_tokens, output_tokens, request_count}`
- TTL: 35 days (giữ data qua tháng)

**Operations**:
- `GET` - Lấy usage hiện tại
- `SET` - Update usage với TTL
- Atomic read-modify-write

**Fallback**: Auto fallback về in-memory cost guard nếu Redis down

---

## Files Đã Cập Nhật

### 1. `backend_ai/app/main_v3.py`

**Imports mới**:
```python
from app.rate_limiter_redis import check_rate_limit_redis, get_rate_limit_stats_redis
from app.cost_guard_redis import check_budget_redis, record_usage_redis, get_usage_redis
from app.redis_client import RedisClient
```

**Lifespan updates**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    - Initialize Redis connection
    - Load RAG agent
    
    yield
    
    # Shutdown
    - Close Redis connection gracefully
```

**New endpoint: `/ready`**:
```python
@app.get("/ready")
async def ready():
    """
    Readiness probe - sẵn sàng nhận traffic chưa?
    
    Checks:
    - Redis connection (nếu enabled)
    - RAG agent loaded
    
    Returns:
    - 200: ready hoặc degraded (Redis down nhưng có fallback)
    - 503: not_ready (RAG agent không load được)
    """
```

**Enhanced `/health`**:
- Liveness probe đơn giản
- Chỉ check container còn sống không
- Không check dependencies (để tránh false positive)

**Updated dependencies**:
- `/chat`: Dùng `check_rate_limit_redis`, `check_budget_redis`
- `/usage`: Dùng `get_usage_redis`, `get_rate_limit_stats_redis`

### 2. `docker-compose.yml`

**Thêm Redis service**:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
  restart: unless-stopped
```

**Backend environment**:
```yaml
environment:
  - REDIS_URL=redis://redis:6379/0
  - REDIS_ENABLED=true
```

**Backend depends_on**:
```yaml
depends_on:
  redis:
    condition: service_healthy  # Đợi Redis healthy mới start
  qdrant:
    condition: service_started
```

**Volume**:
```yaml
volumes:
  redis_data:  # Persist Redis data
```

---

## Cách Sử Dụng

### 1. Local Development (Không Redis)

File `.env`:
```bash
REDIS_ENABLED=false
```

Chạy:
```bash
python -m app.main_v3  # from backend_ai directory
```

**Behavior**: Dùng in-memory rate limiter + cost guard (như TASK 3)

### 2. Local Development (Với Redis)

Start Redis:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

File `.env`:
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true
```

Chạy:
```bash
python -m app.main_v3
```

**Behavior**: Dùng Redis-based rate limiter + cost guard

### 3. Docker Compose (Full Stack)

```bash
docker compose up --build
```

**Services**:
- `backend`: FastAPI app (port 8000)
- `redis`: Redis 7 (port 6379)
- `qdrant`: Vector DB (port 6333)
- `frontend`: Streamlit (port 8501)

**Behavior**: Backend tự động connect Redis trong container network

---

## Testing Guide

### Test 1: Health Check (Liveness)

```bash
curl http://localhost:8000/health
```

**Expected**:
```json
{
  "status": "ok",
  "app": "Chatbot Tài Xế Xanh SM",
  "version": "1.0.0",
  "environment": "development"
}
```

### Test 2: Readiness Check

**Khi Redis healthy**:
```bash
curl http://localhost:8000/ready
```

**Expected** (200 OK):
```json
{
  "status": "ready",
  "app": "Chatbot Tài Xế Xanh SM",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "redis": "ok",
    "rag_agent": "ok"
  }
}
```

**Khi Redis down nhưng có fallback**:
```bash
# Stop Redis
docker stop xanhsm-redis

curl http://localhost:8000/ready
```

**Expected** (200 OK, degraded):
```json
{
  "status": "degraded",
  "checks": {
    "redis": "degraded",
    "rag_agent": "ok"
  }
}
```

**Khi RAG agent không load được**:
**Expected** (503 Service Unavailable):
```json
{
  "status": "not_ready",
  "checks": {
    "redis": "ok",
    "rag_agent": "error: ..."
  }
}
```

### Test 3: Redis Rate Limiting

```bash
# Gửi 11 requests
for i in {1..11}; do
  curl http://localhost:8000/chat -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
    -d '{"message":"test"}' \
    -w "\nHTTP Status: %{http_code}\n"
  sleep 0.5
done
```

**Expected**: Request 11 nhận 429

**Verify trong Redis**:
```bash
docker exec -it xanhsm-redis redis-cli

# List all rate limit keys
KEYS rate_limit:*

# Check user's requests
ZRANGE rate_limit:user_a1b2c3d4 0 -1 WITHSCORES
```

### Test 4: Redis Cost Guard

```bash
# Gửi vài requests
curl http://localhost:8000/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
  -d '{"message":"Điều khoản bảo hiểm là gì?"}'

# Check usage
curl http://localhost:8000/usage \
  -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32"
```

**Verify trong Redis**:
```bash
docker exec -it xanhsm-redis redis-cli

# List all cost guard keys
KEYS cost_guard:*

# Check user's usage
GET cost_guard:user_a1b2c3d4:2026-04
```

**Expected**:
```json
{"input_tokens":120,"output_tokens":450,"request_count":5}
```

### Test 5: Fallback Mechanism

```bash
# Start app với Redis
docker compose up -d

# Gửi request (dùng Redis)
curl http://localhost:8000/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
  -d '{"message":"test"}'

# Stop Redis
docker stop xanhsm-redis

# Gửi request (fallback to in-memory)
curl http://localhost:8000/chat -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: xanhsm-dev-key-2026-dj4334**32" \
  -d '{"message":"test"}'
```

**Expected**: Request vẫn thành công, log warning "Redis not available, using in-memory"

### Test 6: Graceful Shutdown

```bash
# Start app
python -m app.main_v3

# Send SIGTERM (Ctrl+C)
# Hoặc: kill -TERM <pid>
```

**Expected logs**:
```
INFO: Shutting down gracefully...
INFO: Redis connection closed
INFO: Shutdown complete.
```

---

## Architecture Decisions

### 1. Redis vs In-Memory

**Redis (Production)**:
- ✅ Persist data qua restart
- ✅ Shared state giữa nhiều instances
- ✅ Scale horizontal
- ❌ Thêm dependency
- ❌ Network latency

**In-Memory (Development)**:
- ✅ Đơn giản, không cần external service
- ✅ Latency thấp
- ❌ Mất data khi restart
- ❌ Không scale được

**Decision**: Dùng Redis cho production, fallback về in-memory nếu Redis down

### 2. Fallback Strategy

**Option 1**: Fail fast (throw error nếu Redis down)
- ✅ Rõ ràng, dễ debug
- ❌ Downtime khi Redis down

**Option 2**: Fallback to in-memory
- ✅ High availability
- ✅ Graceful degradation
- ❌ Inconsistent state giữa instances

**Decision**: Fallback to in-memory + log warning
- Lý do: Availability > Consistency cho rate limiting
- Trade-off: Mỗi instance có rate limit riêng khi Redis down

### 3. Health Check Strategy

**Liveness (`/health`)**:
- Đơn giản, chỉ check container còn sống
- Không check dependencies
- Kubernetes/Railway restart nếu fail

**Readiness (`/ready`)**:
- Check dependencies (Redis, RAG agent)
- Return 200 nếu degraded (Redis down nhưng có fallback)
- Return 503 nếu not_ready (RAG agent không load)
- Kubernetes/Railway không route traffic nếu 503

**Decision**: Tách biệt liveness và readiness
- Lý do: Tránh restart loop khi Redis down tạm thời

### 4. Redis Data Structures

**Rate Limiting**: Sorted Set (ZSET)
- ✅ Efficient range queries (ZREMRANGEBYSCORE)
- ✅ Atomic operations
- ✅ O(log N) complexity

**Cost Guard**: String (JSON)
- ✅ Đơn giản
- ✅ Atomic read-modify-write
- ❌ Không support increment atomic (phải GET + SET)

**Alternative**: Redis Hash
- ✅ Support HINCRBY (atomic increment)
- ❌ Phức tạp hơn cho use case này

**Decision**: String (JSON) cho cost guard
- Lý do: Đơn giản, đủ cho use case hiện tại

---

## Production Considerations

### 1. Redis Configuration

**Memory**:
```bash
maxmemory 256mb
maxmemory-policy allkeys-lru
```
- Giới hạn memory để tránh OOM
- LRU eviction: xóa keys cũ nhất khi hết memory

**Persistence**:
```bash
appendonly yes
```
- AOF (Append Only File) để persist data
- Trade-off: Slower write, safer data

**Alternative**: RDB snapshots
- Faster write, risk mất data giữa snapshots

### 2. Redis on Railway

Railway cung cấp Redis addon:
- Managed service (không cần config)
- Auto-scaling
- Backup tự động
- Connection string: `REDIS_URL` environment variable

**Setup**:
1. Railway dashboard → Add Redis addon
2. Copy `REDIS_URL` từ addon
3. Set `REDIS_ENABLED=true` trong environment

### 3. Monitoring

**Metrics cần track**:
- Redis connection errors
- Fallback rate (얼마% requests dùng fallback)
- Rate limit hit rate
- Budget exceeded rate
- Redis memory usage
- Redis command latency

**Tools**:
- Railway metrics dashboard
- Redis `INFO` command
- Application logs (structured JSON)

### 4. Scaling

**Horizontal Scaling** (nhiều backend instances):
- ✅ Redis shared state → consistent rate limiting
- ✅ Load balancer distribute traffic
- ⚠️ Nếu Redis down → mỗi instance có limit riêng

**Vertical Scaling** (tăng resources):
- Redis memory: 256MB → 512MB → 1GB
- Backend CPU/RAM: theo load

---

## Known Limitations

### 1. Fallback Inconsistency
- **Issue**: Khi Redis down, mỗi instance có rate limit riêng
- **Impact**: User có thể vượt limit nếu requests đi qua nhiều instances
- **Mitigation**: Monitor Redis uptime, alert nếu down

### 2. Cost Guard Accuracy
- **Issue**: Token estimation không chính xác 100%
- **Impact**: Budget tracking có thể sai lệch 10-20%
- **Mitigation**: Dùng `tiktoken` hoặc parse từ OpenAI response

### 3. Redis Single Point of Failure
- **Issue**: Nếu Redis down, fallback về in-memory (inconsistent)
- **Impact**: Rate limiting không consistent giữa instances
- **Mitigation**: Redis replication (master-slave) hoặc Redis Cluster

### 4. No Distributed Locking
- **Issue**: Cost guard không dùng distributed lock
- **Impact**: Race condition khi nhiều instances update cùng lúc
- **Mitigation**: Acceptable cho use case này (budget tracking không cần strict consistency)

---

## Next Steps (TASK 5)

1. **Nginx Load Balancer**
   - Distribute traffic giữa nhiều backend instances
   - Health check integration
   - SSL termination

2. **Multiple Backend Instances**
   - Scale backend to 3 instances
   - Test Redis shared state
   - Verify rate limiting consistency

3. **Performance Testing**
   - Load test với nhiều concurrent users
   - Measure Redis latency
   - Identify bottlenecks

---

## Checklist

- [x] `redis_client.py` - Centralized Redis connection
- [x] `rate_limiter_redis.py` - Redis-based rate limiter
- [x] `cost_guard_redis.py` - Redis-based cost guard
- [x] Update `main_v3.py` - Use Redis versions
- [x] Enhanced `/health` endpoint
- [x] New `/ready` endpoint
- [x] Graceful shutdown
- [x] Update `docker-compose.yml` - Add Redis service
- [x] Fallback mechanism
- [x] Testing guide
- [x] Documentation

**STATUS**: ✅ TASK 4 HOÀN THÀNH

---

## References

- [Redis Documentation](https://redis.io/docs/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Kubernetes Health Checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Railway Redis](https://docs.railway.app/databases/redis)
- [Graceful Shutdown Best Practices](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-terminating-with-grace)
