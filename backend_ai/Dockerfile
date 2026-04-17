# ============================================================
# PRODUCTION Dockerfile — Multi-stage build
# Chatbot Tài Xế Xanh SM
#
# Mục tiêu: 
#   - Image size < 1GB (ideally < 800MB)
#   - Secure (non-root user)
#   - Production-ready (health checks, graceful shutdown)
#
# Multi-stage benefits:
#   Stage 1 (builder): Install dependencies với build tools
#   Stage 2 (runtime): Chỉ copy runtime files → nhỏ và sạch
# ============================================================

# ──────────────────────────────────────────────────────────
# STAGE 1: Builder
# Cài đặt tất cả dependencies (numpy, faiss, sentence-transformers)
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
# gcc, g++: compile numpy, scipy
# libgomp1: OpenMP support cho sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và install
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Verify critical packages installed
RUN python -c "import fastapi; import langchain; import faiss; import sentence_transformers; print('✅ All packages installed')"


# ──────────────────────────────────────────────────────────
# STAGE 2: Runtime
# Chỉ copy những gì cần để CHẠY
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY app/ /app/app/

# Copy knowledge base (for Railway deployment)
# Note: Nếu KB quá lớn, consider download from S3 at startup
COPY data_pipeline/db_setup /app/data_pipeline/db_setup

# Create directories for data (will be mounted as volumes)
RUN mkdir -p /app/data_pipeline/db_setup && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python path
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# Environment defaults (can be overridden)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV ENVIRONMENT=production
ENV LOG_FORMAT=json

# Expose port
EXPOSE 8000

# Health check
# Docker sẽ tự restart container nếu health check fail
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Start command
# Railway provides PORT via environment variable
# Use $PORT if available, fallback to 8000
CMD ["sh", "-c", "python -m uvicorn app.main_v3:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ============================================================
# BUILD & RUN INSTRUCTIONS
# ============================================================
#
# Build from project root:
#   cd NhomA1-C401-Day06
#   docker build -f backend_ai/Dockerfile -t xanhsm-agent:production backend_ai
#
# Check image size:
#   docker images xanhsm-agent:production
#
# Run with .env file:
#   docker run -p 8000:8000 --env-file .env \
#     -v $(pwd)/data_pipeline/db_setup:/app/data_pipeline/db_setup \
#     xanhsm-agent:production
#
# Run with environment variables:
#   docker run -p 8000:8000 \
#     -e OPENAI_API_KEY=sk-... \
#     -e AGENT_API_KEY=secret \
#     -e ENVIRONMENT=production \
#     -v $(pwd)/data_pipeline/db_setup:/app/data_pipeline/db_setup \
#     xanhsm-agent:production
#
# Test health check:
#   curl http://localhost:8000/health
#
# ============================================================
