#!/usr/bin/env python3
"""
Fish Watcher Setup Wizard - Interactive setup for Telegram.
Run this and it outputs messages suitable for Telegram conversation.
"""

import os
import sys
import json
import yaml
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def step_check_install():
    """Step 1: Check installation."""
    fw_dir = Path(__file__).parent.parent
    
    if not (fw_dir / "run.py").exists():
        return {
            "step": "install",
            "status": "missing",
            "message": "🐟 **Fish Watcher Setup**\n\nI don't see Fish Watcher installed. Want me to set it up for you?",
            "options": ["Yes, install it", "No, cancel"]
        }
    
    return {
        "step": "install",
        "status": "ok",
        "message": "✅ Fish Watcher is installed.",
        "next": "cameras"
    }


def step_find_cameras():
    """Step 2: Find available cameras."""
    import cv2
    
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append({"device": i, "resolution": f"{w}x{h}"})
            cap.release()
    
    if not cameras:
        return {
            "step": "cameras",
            "status": "none_found",
            "message": "📷 **No cameras found!**\n\nPlug in your USB camera and tell me when ready.\n\nOr if using a phone as webcam, tell me the app (DroidCam, Iriun, etc.) and I'll help configure it.",
            "options": ["Camera plugged in", "Using phone as webcam", "Cancel setup"]
        }
    
    if len(cameras) == 1:
        return {
            "step": "cameras", 
            "status": "one_found",
            "device": cameras[0]["device"],
            "message": f"📷 **Found 1 camera** (Device {cameras[0]['device']}, {cameras[0]['resolution']})\n\nIs this the one pointing at your fish tank?",
            "options": ["Yes, use this one", "No, that's wrong", "Cancel setup"]
        }
    
    options = [f"Camera {c['device']} ({c['resolution']})" for c in cameras]
    options.append("None of these / Cancel")
    
    return {
        "step": "cameras",
        "status": "multiple_found", 
        "cameras": cameras,
        "message": f"📷 **Found {len(cameras)} cameras**\n\nWhich one is pointing at your fish tank?",
        "options": options
    }


def step_test_camera(device: int):
    """Step 3: Test the selected camera."""
    import cv2
    
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        return {
            "step": "test",
            "status": "failed",
            "message": f"❌ Couldn't open camera {device}. Try unplugging and replugging it.",
            "options": ["Try again", "Pick different camera", "Cancel"]
        }
    
    # Capture test frame
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return {
            "step": "test",
            "status": "failed",
            "message": "❌ Camera opened but couldn't capture frame.",
            "options": ["Try again", "Pick different camera", "Cancel"]
        }
    
    # Save test frame
    fw_dir = Path(__file__).parent.parent
    test_path = fw_dir / "test_snapshot.jpg"
    cv2.imwrite(str(test_path), frame)
    
    return {
        "step": "test",
        "status": "ok",
        "snapshot_path": str(test_path),
        "message": "📸 **Test snapshot captured!**\n\nI'm sending you the image - does it show your fish tank?",
        "options": ["Yes, looks good!", "No, wrong camera", "Cancel"]
    }


def step_save_config(device: int):
    """Step 4: Save configuration."""
    fw_dir = Path(__file__).parent.parent
    config_path = fw_dir / "config.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    config["camera"]["device"] = device
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return {
        "step": "config",
        "status": "saved",
        "device": device,
        "message": f"✅ **Configuration saved!**\n\nCamera {device} is now set as your fish tank camera.",
        "next": "start"
    }


def step_start_watcher():
    """Step 5: Offer to start watching."""
    return {
        "step": "start",
        "status": "ready",
        "message": "🐟 **Ready to watch!**\n\nWant me to start monitoring your tank now?\n\nI'll run in the background and alert you if anything happens.",
        "options": ["Yes, start watching!", "Not yet, I'll start later"]
    }


def step_complete():
    """Setup complete."""
    return {
        "step": "complete",
        "status": "done",
        "message": """🎉 **Fish Watcher is running!**

I'm now monitoring your tank 24/7. Here's what I'll do:

🚨 **Alert you** if fish stop moving, act weird, or water looks off
📹 **Save clips** of any issues (10 sec before + 30 sec after)
✨ **Capture cool moments** like feeding frenzies
📊 **Send daily reports** on tank health

**Quick commands:**
• "How are my fish?" - current status
• "Show me the tank" - live snapshot
• "Fish report" - today's summary
• "Stop fish watcher" - pause monitoring

Your fish are in good hands! 🐟"""
    }


def run_wizard(current_step: str = None, input_data: dict = None):
    """Run the setup wizard, outputting JSON for each step."""
    
    if current_step is None:
        # Start fresh
        result = step_check_install()
        if result.get("next") == "cameras":
            result = step_find_cameras()
        print(json.dumps(result, indent=2))
        return
    
    if current_step == "cameras":
        if input_data and "device" in input_data:
            result = step_test_camera(input_data["device"])
            print(json.dumps(result, indent=2))
            return
        result = step_find_cameras()
        print(json.dumps(result, indent=2))
        return
    
    if current_step == "test":
        if input_data and input_data.get("confirmed"):
            result = step_save_config(input_data["device"])
            if result.get("next") == "start":
                result = step_start_watcher()
            print(json.dumps(result, indent=2))
            return
    
    if current_step == "start":
        if input_data and input_data.get("start"):
            # Actually start the watcher
            from clawdbot.controller import start
            start()
            result = step_complete()
            print(json.dumps(result, indent=2))
            return
    
    # Default: start from beginning
    result = step_check_install()
    print(json.dumps(result, indent=2))


def main():
    """CLI entry point."""
    step = sys.argv[1] if len(sys.argv) > 1 else None
    data = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    
    run_wizard(step, data)


if __name__ == "__main__":
    main()
