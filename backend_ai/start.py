#!/usr/bin/env python3
import os
import sys

print(f"[DEBUG] OPENAI_API_KEY from os.environ = '{os.environ.get('OPENAI_API_KEY', 'NOT_FOUND')}'")
def main():
    # DEBUG: In ra để xem Railway có inject đúng không
    print("=== ENV CHECK ===")
    print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    print(f"AGENT_API_KEY: {'SET' if os.environ.get('AGENT_API_KEY') else 'NOT SET'}")
    print(f"OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
    print("=================")
    
    port = os.environ.get("PORT", "8000")
    print(f"Starting uvicorn on port {port}...")
    
    import uvicorn
    uvicorn.run(
        "app.main_v3:app",
        host="0.0.0.0",
        port=int(port),
        log_level="info"
    )

if __name__ == "__main__":
    main()