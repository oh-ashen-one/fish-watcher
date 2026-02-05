#!/usr/bin/env python3
"""
Fish Watcher Dashboard - Entry Point

Usage:
    python dashboard.py
    python dashboard.py --port 8080
    python dashboard.py --host 0.0.0.0 --port 8080  # Allow LAN access
"""

import argparse
import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Fish Watcher Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to run on (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
    
    print("🐟 Fish Watcher Dashboard")
    print(f"📍 http://{args.host}:{args.port}")
    print()
    
    import uvicorn
    uvicorn.run(
        "dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
