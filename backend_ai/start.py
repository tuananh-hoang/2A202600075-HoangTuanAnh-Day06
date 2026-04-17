#!/usr/bin/env python3
"""
Railway startup script - handles PORT environment variable
"""
import os
import sys

def main():
    # Get PORT from environment, default to 8000
    port = os.environ.get("PORT", "8000")
    
    print(f"Starting uvicorn on port {port}...")
    
    # Import and run uvicorn programmatically
    import uvicorn
    
    uvicorn.run(
        "app.main_v3:app",
        host="0.0.0.0",
        port=int(port),
        log_level="info"
    )

if __name__ == "__main__":
    main()
