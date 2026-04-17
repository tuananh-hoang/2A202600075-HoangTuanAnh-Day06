#!/bin/sh
# Railway startup script - handles PORT environment variable

# Use Railway's PORT or default to 8000
PORT=${PORT:-8000}
echo "DEBUG OPENAI_API_KEY=${OPENAI_API_KEY:0:10}..."
echo "Starting uvicorn on port $PORT..."
exec python -m uvicorn app.main_v3:app --host 0.0.0.0 --port "$PORT"
