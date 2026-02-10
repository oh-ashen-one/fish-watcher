"""
Main Fish Watcher - ties everything together.
"""

import time
import signal
import sys
from pathlib import Path
from typing import Optional
import cv2
import yaml

from .buffer import RollingBuffer
from .detector import FishWatcherDetector, DetectorConfig, Alert
from .recorder import ClipRecorder
from .notifier import ClawdbotNotifier, WebhookNotifier
from .reports import ReportGenerator


class FishWatcher:
    """Main watcher class that monitors a camera feed."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        
        # Initialize components
        self.buffer = RollingBuffer(
            max_seconds=self.config['recording']['pre_roll'],
            fps=self.config['camera']['fps']
        )
        
        detector_config = DetectorConfig(
            motion_sensitivity=self.config['detection']['motion_sensitivity'],
            no_motion_threshold=self.config['detection']['no_motion_threshold'],
            color_change_threshold=self.config['detection']['color_change_threshold'],
            surface_zone_percent=self.config['detection']['surface_zone_percent'],
            learn_baseline=self.config['detection']['learn_baseline'],
        )
        self.detector = FishWatcherDetector(detector_config)
        self.detector.cooldown = self.config['alerts']['cooldown']
        
        self.recorder = ClipRecorder(
            output_dir=self.config['recording']['output_dir'],
            pre_roll=self.config['recording']['pre_roll'],
            post_roll=self.config['recording']['post_roll'],
            fps=self.config['camera']['fps'],
            format=self.config['recording']['format'],
        )
        
        # Setup notifier
        if self.config['notification']['method'] == 'webhook':
            self.notifier = WebhookNotifier(self.config['notification'].get('webhook_url', ''))
        else:
            self.notifier = ClawdbotNotifier()
        
        # Setup reports
        self.reports = ReportGenerator(
            data_dir=self.config.get('reports', {}).get('data_dir', './data')
        )
        
        self.camera: Optional[cv2.VideoCapture] = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def _setup_camera(self) -> cv2.VideoCapture:
        """Initialize the camera connection."""
        cam_config = self.config['camera']
        
        if cam_config['type'] == 'usb':
            cap = cv2.VideoCapture(cam_config['device'])
        else:
            cap = cv2.VideoCapture(cam_config.get('url', 0))
        
        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_config['width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_config['height'])
        cap.set(cv2.CAP_PROP_FPS, cam_config['fps'])
        
        if not cap.isOpened():
            raise RuntimeError("Failed to open camera")
        
        return cap
    
    def start(self) -> None:
        """Start the watcher."""
        print("[FishWatcher] Starting...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.camera = self._setup_camera()
        self.running = True
        
        print("[FishWatcher] Camera connected. Watching...")
        print(f"[FishWatcher] Pre-roll: {self.config['recording']['pre_roll']}s")
        print(f"[FishWatcher] Post-roll: {self.config['recording']['post_roll']}s")
        
        frame_count = 0
        last_status = time.time()
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                
                if not ret:
                    print("[FishWatcher] Failed to read frame, reconnecting...")
                    time.sleep(1)
                    self.camera = self._setup_camera()
                    continue
                
                # Add to rolling buffer
                self.buffer.add(frame)
                
                # If recording, add frame to recorder
                if self.recorder.is_recording:
                    clip_path, alert = self.recorder.add_frame(frame)
                    if clip_path:
                        # Recording complete, send notification
                        self._send_notification(alert, clip_path)
                        self.reports.record_clip()
                
                # Run detection (skip if actively recording)
                if not self.recorder.is_recording:
                    alerts = self.detector.process(frame)
                    
                    for alert in alerts:
                        print(f"[FishWatcher] Alert: {alert.type.value} - {alert.message}")
                        self.reports.record_alert(alert.type.value, alert.is_cool_moment)
                        self.recorder.start_recording(self.buffer, alert)
                        break  # Only handle one alert at a time
                
                frame_count += 1
                
                # Status update every 60 seconds
                if time.time() - last_status > 60:
                    print(f"[FishWatcher] Status: {frame_count} frames processed, buffer: {len(self.buffer)} frames")
                    last_status = time.time()
                
                # Small delay to control frame rate
                time.sleep(1 / self.config['camera']['fps'])
                
        except Exception as e:
            print(f"[FishWatcher] Error: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the watcher."""
        print("[FishWatcher] Stopping...")
        self.running = False
        
        if self.camera:
            self.camera.release()
        
        print("[FishWatcher] Stopped.")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print(f"\n[FishWatcher] Received signal {signum}")
        self.running = False
    
    def _send_notification(self, alert: Optional[Alert], clip_path: str) -> None:
        """Send notification for completed clip."""
        if not alert:
            return
        
        result = self.notifier.notify(alert, clip_path)
        if result.success:
            print(f"[FishWatcher] Notification sent: {result.message}")
        else:
            print(f"[FishWatcher] Notification failed: {result.message}")


def main() -> None:
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fish Tank Watcher")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()
    
    watcher = FishWatcher(config_path=args.config)
    watcher.start()


if __name__ == "__main__":
    main()
