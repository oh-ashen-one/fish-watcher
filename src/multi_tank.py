"""
Multi-Tank Support for Fish Watcher.
Monitor multiple fish tanks simultaneously from one instance.
"""

import os
import time
import signal
import threading
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import cv2
import yaml

from .buffer import RollingBuffer
from .detector import FishWatcherDetector, DetectorConfig, Alert
from .recorder import ClipRecorder
from .notifier import ClawdbotNotifier
from .reports import ReportGenerator


@dataclass
class TankConfig:
    """Configuration for a single tank."""
    id: str
    name: str
    camera_type: str = "usb"
    camera_device: int = 0
    camera_url: str = ""
    width: int = 640
    height: int = 480
    fps: int = 15
    
    # Detection settings
    motion_sensitivity: int = 50
    no_motion_threshold: int = 300
    
    # Fish profiles
    fish_count: int = 0
    fish_profiles: List[dict] = field(default_factory=list)
    
    # Output directories (auto-generated if not set)
    clips_dir: str = ""
    data_dir: str = ""
    
    def __post_init__(self):
        if not self.clips_dir:
            self.clips_dir = f"./clips/{self.id}"
        if not self.data_dir:
            self.data_dir = f"./data/{self.id}"


class TankWatcher:
    """Watcher for a single tank (runs in its own thread)."""
    
    def __init__(self, tank_config: TankConfig, notifier: ClawdbotNotifier):
        self.config = tank_config
        self.notifier = notifier
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Initialize components
        self.buffer = RollingBuffer(max_seconds=10, fps=tank_config.fps)
        
        detector_config = DetectorConfig(
            motion_sensitivity=tank_config.motion_sensitivity,
            no_motion_threshold=tank_config.no_motion_threshold,
        )
        self.detector = FishWatcherDetector(detector_config)
        
        # Ensure output dirs exist
        Path(tank_config.clips_dir).mkdir(parents=True, exist_ok=True)
        Path(tank_config.data_dir).mkdir(parents=True, exist_ok=True)
        
        self.recorder = ClipRecorder(
            output_dir=tank_config.clips_dir,
            pre_roll=10,
            post_roll=30,
            fps=tank_config.fps,
        )
        
        self.reports = ReportGenerator(data_dir=tank_config.data_dir)
        self.camera: Optional[cv2.VideoCapture] = None
        
        # Stats
        self.frame_count = 0
        self.last_frame_time = 0
        self.status = "stopped"
        self.last_error = ""
        
    def _setup_camera(self) -> cv2.VideoCapture:
        """Initialize camera connection."""
        if self.config.camera_type == "usb":
            cap = cv2.VideoCapture(self.config.camera_device)
        else:
            cap = cv2.VideoCapture(self.config.camera_url)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        cap.set(cv2.CAP_PROP_FPS, self.config.fps)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open camera for tank {self.config.name}")
        
        return cap
    
    def start(self) -> None:
        """Start watching this tank (in background thread)."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"[{self.config.name}] Started watching")
    
    def stop(self) -> None:
        """Stop watching this tank."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.camera:
            self.camera.release()
        self.status = "stopped"
        print(f"[{self.config.name}] Stopped")
    
    def _run_loop(self) -> None:
        """Main watch loop (runs in thread)."""
        try:
            self.camera = self._setup_camera()
            self.status = "running"
            frame_time = 1.0 / self.config.fps
            
            while self.running:
                start = time.time()
                ret, frame = self.camera.read()
                
                if not ret:
                    self.status = "reconnecting"
                    self.last_error = "Failed to read frame"
                    time.sleep(1)
                    try:
                        self.camera = self._setup_camera()
                        self.status = "running"
                    except Exception as e:
                        self.last_error = str(e)
                    continue
                
                self.last_frame_time = time.time()
                self.buffer.add(frame)
                
                # Handle recording
                if self.recorder.is_recording:
                    clip_path, alert = self.recorder.add_frame(frame)
                    if clip_path:
                        self._send_notification(alert, clip_path)
                        self.reports.record_clip()
                else:
                    # Run detection
                    alerts = self.detector.process(frame)
                    for alert in alerts:
                        print(f"[{self.config.name}] Alert: {alert.type.value}")
                        self.reports.record_alert(alert.type.value, alert.is_cool_moment)
                        self.recorder.start_recording(self.buffer, alert)
                        break
                
                self.frame_count += 1
                
                # Rate limiting
                elapsed = time.time() - start
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
                    
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            print(f"[{self.config.name}] Error: {e}")
        finally:
            if self.camera:
                self.camera.release()
    
    def _send_notification(self, alert: Optional[Alert], clip_path: str) -> None:
        """Send notification with tank name included."""
        if not alert:
            return
        
        # Modify alert message to include tank name
        alert.message = f"[{self.config.name}] {alert.message}"
        result = self.notifier.notify(alert, clip_path)
        if result.success:
            print(f"[{self.config.name}] Notification sent")
    
    def get_snapshot(self) -> Optional[bytes]:
        """Get current frame as JPEG bytes."""
        if not self.camera or not self.running:
            return None
        
        ret, frame = self.camera.read()
        if not ret:
            return None
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()
    
    def get_status(self) -> dict:
        """Get current status for this tank."""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "status": self.status,
            "frame_count": self.frame_count,
            "last_frame_time": self.last_frame_time,
            "last_error": self.last_error,
            "is_recording": self.recorder.is_recording,
        }


class MultiTankWatcher:
    """Manages multiple tank watchers."""
    
    def __init__(self, config_path: str = "tanks.yaml"):
        self.config_path = config_path
        self.tanks: Dict[str, TankWatcher] = {}
        self.notifier = ClawdbotNotifier()
        self.running = False
        
    def load_config(self) -> List[TankConfig]:
        """Load tank configurations from YAML."""
        path = Path(self.config_path)
        if not path.exists():
            print(f"Config file {self.config_path} not found")
            return []
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        tanks = []
        for tank_data in data.get("tanks", []):
            tank = TankConfig(
                id=tank_data.get("id", f"tank_{len(tanks)+1}"),
                name=tank_data.get("name", f"Tank {len(tanks)+1}"),
                camera_type=tank_data.get("camera", {}).get("type", "usb"),
                camera_device=tank_data.get("camera", {}).get("device", 0),
                camera_url=tank_data.get("camera", {}).get("url", ""),
                width=tank_data.get("camera", {}).get("width", 640),
                height=tank_data.get("camera", {}).get("height", 480),
                fps=tank_data.get("camera", {}).get("fps", 15),
                motion_sensitivity=tank_data.get("detection", {}).get("motion_sensitivity", 50),
                no_motion_threshold=tank_data.get("detection", {}).get("no_motion_threshold", 300),
                fish_count=tank_data.get("fish", {}).get("count", 0),
                fish_profiles=tank_data.get("fish", {}).get("profiles", []),
                clips_dir=tank_data.get("clips_dir", ""),
                data_dir=tank_data.get("data_dir", ""),
            )
            tanks.append(tank)
        
        return tanks
    
    def start(self) -> None:
        """Start all tank watchers."""
        configs = self.load_config()
        
        if not configs:
            print("[MultiTank] No tanks configured")
            return
        
        print(f"[MultiTank] Starting {len(configs)} tank(s)...")
        
        for config in configs:
            watcher = TankWatcher(config, self.notifier)
            self.tanks[config.id] = watcher
            watcher.start()
        
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print(f"[MultiTank] All tanks started. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop all tank watchers."""
        print("[MultiTank] Stopping all tanks...")
        self.running = False
        
        for watcher in self.tanks.values():
            watcher.stop()
        
        print("[MultiTank] All tanks stopped.")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self.running = False
    
    def get_tank(self, tank_id: str) -> Optional[TankWatcher]:
        """Get a specific tank watcher."""
        return self.tanks.get(tank_id)
    
    def get_all_status(self) -> List[dict]:
        """Get status for all tanks."""
        return [watcher.get_status() for watcher in self.tanks.values()]
    
    def add_tank(self, config: TankConfig) -> TankWatcher:
        """Add a new tank at runtime."""
        watcher = TankWatcher(config, self.notifier)
        self.tanks[config.id] = watcher
        if self.running:
            watcher.start()
        return watcher
    
    def remove_tank(self, tank_id: str) -> bool:
        """Remove a tank at runtime."""
        if tank_id not in self.tanks:
            return False
        
        self.tanks[tank_id].stop()
        del self.tanks[tank_id]
        return True


def main():
    """Entry point for multi-tank mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fish Watcher - Multi-Tank Mode")
    parser.add_argument("-c", "--config", default="tanks.yaml", help="Tanks config file")
    args = parser.parse_args()
    
    watcher = MultiTankWatcher(config_path=args.config)
    watcher.start()


if __name__ == "__main__":
    main()
