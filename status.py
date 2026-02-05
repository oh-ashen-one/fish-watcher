#!/usr/bin/env python3
"""
Fish Watcher Status Check
Quick health check for camera, config, and recent activity.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import yaml

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def check_config():
    """Check if config exists and is valid."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        return False, "config.yaml not found"
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return True, config
    except Exception as e:
        return False, f"Config parse error: {e}"


def check_camera(config):
    """Test camera connection."""
    if not CV2_AVAILABLE:
        return None, "OpenCV not installed"
    
    cam_config = config.get("camera", {})
    cam_type = cam_config.get("type", "usb")
    
    if cam_type == "usb":
        device = cam_config.get("device", 0)
        cap = cv2.VideoCapture(device)
    else:
        url = cam_config.get("url", "")
        cap = cv2.VideoCapture(url)
    
    if not cap.isOpened():
        return False, f"Failed to open camera ({cam_type})"
    
    ret, frame = cap.read()
    cap.release()
    
    if ret and frame is not None:
        h, w = frame.shape[:2]
        return True, f"Camera OK ({w}x{h})"
    else:
        return False, "Camera opened but no frames"


def check_clips():
    """Check clips directory."""
    clips_dir = Path("clips")
    if not clips_dir.exists():
        return 0, []
    
    clips = list(clips_dir.glob("*.mp4"))
    recent = sorted(clips, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    return len(clips), [c.name for c in recent]


def check_data():
    """Check data directory for reports."""
    data_dir = Path("data")
    if not data_dir.exists():
        return None
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = data_dir / f"daily_{today}.json"
    
    if today_file.exists():
        try:
            with open(today_file) as f:
                return json.load(f)
        except:
            pass
    return None


def main():
    print("🐟 Fish Watcher Status Check")
    print("=" * 40)
    
    # Config check
    ok, result = check_config()
    if ok:
        print(f"✅ Config: OK")
        config = result
    else:
        print(f"❌ Config: {result}")
        config = {}
    
    # Camera check
    if config:
        ok, msg = check_camera(config)
        if ok is None:
            print(f"⚠️  Camera: {msg}")
        elif ok:
            print(f"✅ Camera: {msg}")
        else:
            print(f"❌ Camera: {msg}")
    
    # Clips check
    count, recent = check_clips()
    print(f"📹 Clips: {count} total")
    if recent:
        print(f"   Recent: {recent[0]}")
    
    # Today's data
    data = check_data()
    if data:
        health = data.get("health_score", "?")
        alerts = data.get("alert_count", 0)
        print(f"📊 Today: Health {health}/100, {alerts} alerts")
    else:
        print(f"📊 Today: No data yet")
    
    # Dependencies
    print("\n📦 Dependencies:")
    print(f"   opencv-python: {'✅' if CV2_AVAILABLE else '❌'}")
    
    try:
        import numpy
        print(f"   numpy: ✅ ({numpy.__version__})")
    except:
        print(f"   numpy: ❌")
    
    try:
        import flask
        print(f"   flask: ✅ ({flask.__version__})")
    except:
        print(f"   flask: ❌")
    
    try:
        import anthropic
        print(f"   anthropic: ✅")
    except:
        print(f"   anthropic: ⚠️ (optional, for vision)")
    
    print("\n" + "=" * 40)
    print("Run 'python run.py' to start monitoring")
    print("Run 'python dashboard.py' for web UI")


if __name__ == "__main__":
    main()
