#!/usr/bin/env python3
"""
Quick camera test - checks what cameras are available and captures a test frame.
Run this before starting the full watcher.
"""

import sys
import cv2
import os

def find_cameras():
    """Find all available cameras."""
    print("Scanning for cameras...")
    print()
    
    found = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"  Camera {i}: FOUND - {w}x{h} @ {fps:.0f}fps")
            found.append(i)
            cap.release()
    
    if not found:
        print("  No cameras found!")
        print()
        print("  Tips:")
        print("  - Make sure camera is plugged in")
        print("  - Try unplugging and replugging")
        print("  - Check if another app is using the camera")
    
    print()
    return found


def test_camera(device_id=0):
    """Test a specific camera and save a snapshot."""
    print(f"Testing camera {device_id}...")
    
    cap = cv2.VideoCapture(device_id)
    
    if not cap.isOpened():
        print(f"  Failed to open camera {device_id}")
        return False
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Capture a few frames (first few might be black)
    for _ in range(10):
        ret, frame = cap.read()
    
    if not ret:
        print("  Failed to capture frame")
        cap.release()
        return False
    
    # Save test frame
    test_path = "test_snapshot.jpg"
    cv2.imwrite(test_path, frame)
    print(f"  Saved test snapshot to: {os.path.abspath(test_path)}")
    
    # Get actual settings
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"  Resolution: {w}x{h}")
    print(f"  FPS: {fps:.0f}")
    print(f"  Frame shape: {frame.shape}")
    print()
    print("  Camera working!")
    
    cap.release()
    return True


def main():
    print("=" * 50)
    print("Fish Watcher - Camera Test")
    print("=" * 50)
    print()
    
    # Find cameras
    cameras = find_cameras()
    
    if not cameras:
        sys.exit(1)
    
    # Test first camera found
    device = cameras[0]
    print(f"Testing camera {device}...")
    print()
    
    if test_camera(device):
        print()
        print("=" * 50)
        print("Camera is ready! You can now run:")
        print(f"  python run.py")
        print()
        print("Or if you need a different camera, edit config.yaml:")
        print(f"  device: {device}")
        print("=" * 50)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
