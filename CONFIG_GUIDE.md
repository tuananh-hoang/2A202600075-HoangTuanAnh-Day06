# Configuration Guide

## Overview

Chatbot Xanh SM sử dụng **12-Factor App** principles cho config management:
- ✅ Tất cả config từ environment variables
- ✅ Không hardcode secrets trong code
- ✅ Validation fail-fast
- ✅ Type-safe với Pydantic Settings

## Quick Start

### 1. Copy template

```bash
cp .env.example .env
```

### 2. Fill in required values

```env
# Minimum required
OPENAI_API_KEY=sk-your-key-here
AGENT_API_KEY=your-secret-api-key
```

### 3. Run

```bash
python backend_ai/app/main_v3.py
```

## Configuration Files

### `.env` (local development)
- Chứa secrets và config cục bộ
- **KHÔNG commit vào Git** (đã có trong `.gitignore`)
- Copy từ `.env.example` và điền giá trị thật

### `.env.example` (template)
- Template cho team
- **Commit vào Git**
- Không chứa giá trị thật

### `backend_ai/app/core/config.py` (code)
- Định nghĩa tất cả config fields
- Validation logic
- Default values

## Environment Variables

### Required (Production)

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `AGENT_API_KEY` | API key cho authentication | `my-secret-key-123` |

### Server Config

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `false` | Enable debug mode |

### AI & LLM Config

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `AI_TEMPERATURE` | `0.0` | Temperature (0-1) |
| `MAX_TOKENS` | `500` | Max tokens per response |

### RAG & Retrieval Config

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence transformer model |
| `RETRIEVAL_TOP_K` | `5` | Top K chunks to retrieve |
| `RERANK_TOP_K` | `5` | Top K after reranking |

### Security Config

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `*` | CORS origins (comma-separated) |

### Redis Config (for future tasks)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_ENABLED` | `false` | Enable Redis features |

### Rate Limiting (for future tasks)

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max requests per minute |

### Cost Guard (for future tasks)

| Variable | Default | Description |
|----------|---------|-------------|
| `COST_GUARD_ENABLED` | `false` | Enable cost tracking |
| `MONTHLY_BUDGET_USD` | `10.0` | Monthly budget per user |

### Logging Config

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_FORMAT` | `json` | `json` \| `text` |

## Environment-Specific Config

### Development

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text
ALLOWED_ORIGINS=*
```

### Staging

```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
ALLOWED_ORIGINS=https://staging.xanhsm.com
AGENT_API_KEY=staging-secret-key
```

### Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_FORMAT=json
ALLOWED_ORIGINS=https://xanhsm.com,https://app.xanhsm.com
AGENT_API_KEY=production-secret-key-very-secure
RATE_LIMIT_ENABLED=true
COST_GUARD_ENABLED=true
```

## Validation

Config được validate khi app startup:

### Warnings (không crash)
- ⚠️ `OPENAI_API_KEY` not set → dùng mock LLM
- ⚠️ SQLite/FAISS files not found
- ⚠️ `DEBUG=true` in production
- ⚠️ `ALLOWED_ORIGINS=*` in production

### Errors (crash app)
- ❌ `AGENT_API_KEY` not set in production
- ❌ Invalid config values

## Usage in Code

### Import settings

```python
from app.core.config import settings

# Access config
print(settings.openai_api_key)
print(settings.llm_model)
print(settings.environment)
```

### Check environment

```python
if settings.environment == "production":
    # Production-specific logic
    pass
```

### Get typed values

```python
# All values are type-safe
port: int = settings.port
debug: bool = settings.debug
temperature: float = settings.ai_temperature
```

## Docker & Cloud Deployment

### Docker Compose

```yaml
services:
  backend:
    env_file:
      - .env
    environment:
      - ENVIRONMENT=staging
      - PORT=8000
```

### Railway

```bash
railway variables set OPENAI_API_KEY=sk-...
railway variables set AGENT_API_KEY=my-secret
railway variables set ENVIRONMENT=production
```

### Render

Set environment variables in dashboard:
- Settings → Environment → Add Environment Variable

## Troubleshooting

### "AGENT_API_KEY must be set in production"

**Solution**: Set `AGENT_API_KEY` in `.env` or environment:

```bash
export AGENT_API_KEY=your-secret-key
```

### "OPENAI_API_KEY not set — using mock LLM"

**Solution**: Set `OPENAI_API_KEY` in `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
```

### "SQLite DB not found"

**Solution**: Build knowledge base first:

```bash
python data_pipeline/db_setup/setup_db.py
```

### Config not loading

**Solution**: Check `.env` file location (must be in project root):

```
NhomA1-C401-Day06/
├── .env              ← Here
├── backend_ai/
│   └── app/
│       └── main_v3.py
```

## Best Practices

### ✅ DO

- Use `.env` for local development
- Use platform env vars for cloud deployment
- Keep secrets out of Git
- Validate config on startup
- Use different values per environment

### ❌ DON'T

- Commit `.env` to Git
- Hardcode secrets in code
- Use same API keys for dev/prod
- Skip validation
- Use `DEBUG=true` in production

## Next Steps

After completing TASK 1 (Config Management):
- ✅ TASK 2: Docker Multi-Stage Build
- ✅ TASK 3: API Security (auth, rate limiting, cost guard)
- ✅ TASK 4: Reliability & Health Checks
- ✅ TASK 5: Load Balancing & Scaling
- ✅ TASK 6: Cloud Deployment
