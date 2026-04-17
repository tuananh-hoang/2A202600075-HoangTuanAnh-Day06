#!/bin/sh
PORT=${PORT:-8000}
echo "DEBUG OPENAI_API_KEY=$OPENAI_API_KEY"
echo "Starting uvicorn on port $PORT..."
exec python -m uvicorn app.main_v3:app --host 0.0.0.0 --port "$PORT"