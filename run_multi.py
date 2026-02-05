#!/usr/bin/env python3
"""
Fish Watcher - Multi-Tank Mode
Monitor multiple fish tanks simultaneously.

Usage:
    python run_multi.py
    python run_multi.py -c tanks.yaml
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.multi_tank import MultiTankWatcher


def main():
    parser = argparse.ArgumentParser(
        description="Fish Watcher - Multi-Tank Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_multi.py                  # Use tanks.yaml
    python run_multi.py -c my_tanks.yaml # Custom config

Config format (tanks.yaml):
    tanks:
      - id: "tank1"
        name: "Living Room"
        camera:
          type: "usb"
          device: 0
        fish:
          count: 3
"""
    )
    parser.add_argument(
        "-c", "--config",
        default="tanks.yaml",
        help="Tanks configuration file (default: tanks.yaml)"
    )
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {args.config}")
        print(f"   Copy tanks.example.yaml to {args.config} and customize it.")
        sys.exit(1)
    
    print("🐟 Fish Watcher - Multi-Tank Mode")
    print(f"📁 Config: {args.config}")
    print()
    
    watcher = MultiTankWatcher(config_path=args.config)
    watcher.start()


if __name__ == "__main__":
    main()
