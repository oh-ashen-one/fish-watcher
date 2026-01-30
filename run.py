#!/usr/bin/env python3
"""
Fish Watcher - Entry Point

Usage:
    python run.py
    python run.py --config my-config.yaml
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.watcher import main

if __name__ == "__main__":
    main()
