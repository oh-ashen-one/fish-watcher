#!/usr/bin/env python3
"""
Fish Watcher Controller - CLI for Clawdbot integration.
Provides easy commands for managing fish watcher via Telegram.
"""

import os
import sys
import json
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_fish_watcher_dir() -> Path:
    """Get fish watcher installation directory."""
    # Check common locations
    paths = [
        Path(__file__).parent.parent,
        Path.home() / "clawd" / "repos" / "fish-watcher",
        Path.home() / "fish-watcher",
    ]
    for p in paths:
        if (p / "run.py").exists():
            return p
    return paths[0]


def get_pid_file() -> Path:
    """Get PID file location."""
    return get_fish_watcher_dir() / ".fish-watcher.pid"


def is_running() -> tuple[bool, int]:
    """Check if fish watcher is running. Returns (running, pid)."""
    pid_file = get_pid_file()
    
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True, pid
        except (ProcessLookupError, ValueError):
            pid_file.unlink(missing_ok=True)
    
    return False, 0


def status():
    """Get current status."""
    running, pid = is_running()
    fw_dir = get_fish_watcher_dir()
    
    result = {
        "running": running,
        "pid": pid if running else None,
        "directory": str(fw_dir),
        "config_exists": (fw_dir / "config.yaml").exists(),
        "clips_count": len(list((fw_dir / "clips").glob("*.mp4"))) if (fw_dir / "clips").exists() else 0,
    }
    
    # Check for pending alerts
    alert_file = Path.home() / "clawd" / "fish-watcher-pending-alert.json"
    if alert_file.exists():
        try:
            result["pending_alert"] = json.loads(alert_file.read_text())
        except:
            pass
    
    print(json.dumps(result, indent=2))
    return result


def start():
    """Start fish watcher in background."""
    running, pid = is_running()
    if running:
        print(json.dumps({"success": False, "error": f"Already running (PID {pid})"}))
        return False
    
    fw_dir = get_fish_watcher_dir()
    log_file = fw_dir / "fish-watcher.log"
    pid_file = get_pid_file()
    
    # Start process
    process = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=fw_dir,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    
    # Save PID
    pid_file.write_text(str(process.pid))
    
    print(json.dumps({
        "success": True,
        "pid": process.pid,
        "log_file": str(log_file)
    }))
    return True


def stop():
    """Stop fish watcher."""
    running, pid = is_running()
    if not running:
        print(json.dumps({"success": False, "error": "Not running"}))
        return False
    
    try:
        os.kill(pid, signal.SIGTERM)
        get_pid_file().unlink(missing_ok=True)
        print(json.dumps({"success": True, "stopped_pid": pid}))
        return True
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return False


def list_cameras():
    """List available cameras."""
    import cv2
    
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append({"device": i, "resolution": f"{w}x{h}"})
            cap.release()
    
    print(json.dumps({"cameras": cameras}))
    return cameras


def capture_frame(device: int = 0, output: str = None):
    """Capture a single frame from camera."""
    import cv2
    
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print(json.dumps({"success": False, "error": f"Cannot open camera {device}"}))
        return None
    
    # Capture a few frames to let camera adjust
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(json.dumps({"success": False, "error": "Failed to capture frame"}))
        return None
    
    # Save frame
    if output is None:
        output = get_fish_watcher_dir() / "current_frame.jpg"
    
    cv2.imwrite(str(output), frame)
    print(json.dumps({"success": True, "path": str(output)}))
    return str(output)


def set_config(key: str, value: str):
    """Update a config value."""
    import yaml
    
    config_path = get_fish_watcher_dir() / "config.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Navigate nested keys (e.g., "camera.device")
    keys = key.split(".")
    obj = config
    for k in keys[:-1]:
        obj = obj[k]
    
    # Convert value type
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
    
    obj[keys[-1]] = value
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(json.dumps({"success": True, "key": key, "value": value}))


def get_report(report_type: str = "daily"):
    """Generate a report."""
    sys.path.insert(0, str(get_fish_watcher_dir()))
    from src.reports import ReportGenerator
    
    rg = ReportGenerator(data_dir=str(get_fish_watcher_dir() / "data"))
    
    if report_type == "weekly":
        report = rg.generate_weekly_report()
    else:
        report = rg.generate_daily_report()
    
    print(report)
    return report


def get_pending_alert():
    """Get and clear pending alert."""
    alert_file = Path.home() / "clawd" / "fish-watcher-pending-alert.json"
    
    if not alert_file.exists():
        print(json.dumps({"alert": None}))
        return None
    
    try:
        alert = json.loads(alert_file.read_text())
        alert_file.unlink()  # Clear after reading
        print(json.dumps({"alert": alert}))
        return alert
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return None


def list_clips(limit: int = 10):
    """List recent clips."""
    clips_dir = get_fish_watcher_dir() / "clips"
    
    if not clips_dir.exists():
        print(json.dumps({"clips": []}))
        return []
    
    clips = sorted(clips_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    result = []
    for clip in clips[:limit]:
        result.append({
            "path": str(clip),
            "name": clip.name,
            "size_mb": round(clip.stat().st_size / 1024 / 1024, 2),
            "created": datetime.fromtimestamp(clip.stat().st_mtime).isoformat()
        })
    
    print(json.dumps({"clips": result}))
    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: controller.py <command> [args]")
        print("Commands: status, start, stop, cameras, capture, config, report, alert, clips")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        status()
    elif cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "cameras":
        list_cameras()
    elif cmd == "capture":
        device = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        capture_frame(device)
    elif cmd == "config":
        if len(sys.argv) < 4:
            print("Usage: controller.py config <key> <value>")
            sys.exit(1)
        set_config(sys.argv[2], sys.argv[3])
    elif cmd == "report":
        report_type = sys.argv[2] if len(sys.argv) > 2 else "daily"
        get_report(report_type)
    elif cmd == "alert":
        get_pending_alert()
    elif cmd == "clips":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        list_clips(limit)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
