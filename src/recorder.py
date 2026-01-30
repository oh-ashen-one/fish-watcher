"""
Video clip recorder with pre-roll support.
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

from .buffer import RollingBuffer, BufferedFrame
from .detector import Alert


class ClipRecorder:
    """Records video clips with pre-roll from buffer."""
    
    def __init__(
        self,
        output_dir: str = "./clips",
        pre_roll: int = 10,
        post_roll: int = 30,
        fps: int = 15,
        format: str = "mp4"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pre_roll = pre_roll
        self.post_roll = post_roll
        self.fps = fps
        self.format = format
        
        self.recording = False
        self.recording_start: Optional[float] = None
        self.current_frames: list[np.ndarray] = []
        self.current_alert: Optional[Alert] = None
        self.lock = threading.Lock()
        
    def start_recording(self, buffer: RollingBuffer, alert: Alert) -> None:
        """Start recording a clip, pulling pre-roll from buffer."""
        with self.lock:
            if self.recording:
                return
            
            self.recording = True
            self.recording_start = time.time()
            self.current_alert = alert
            
            # Get pre-roll frames from buffer
            pre_frames = buffer.get_recent(self.pre_roll)
            self.current_frames = [f.frame for f in pre_frames]
            print(f"[Recorder] Started clip with {len(self.current_frames)} pre-roll frames")
    
    def add_frame(self, frame: np.ndarray) -> Optional[str]:
        """Add a frame to current recording. Returns clip path when done."""
        with self.lock:
            if not self.recording:
                return None
            
            self.current_frames.append(frame.copy())
            
            # Check if post-roll complete
            elapsed = time.time() - self.recording_start
            if elapsed >= self.post_roll:
                return self._save_clip()
            
            return None
    
    def _save_clip(self) -> str:
        """Save the current clip to disk."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        alert_type = self.current_alert.type.value if self.current_alert else "unknown"
        filename = f"{timestamp}_{alert_type}.{self.format}"
        filepath = self.output_dir / filename
        
        if not self.current_frames:
            self.recording = False
            return ""
        
        # Get frame dimensions
        h, w = self.current_frames[0].shape[:2]
        
        # Create video writer
        if self.format == "mp4":
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        else:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        writer = cv2.VideoWriter(str(filepath), fourcc, self.fps, (w, h))
        
        for frame in self.current_frames:
            writer.write(frame)
        
        writer.release()
        
        print(f"[Recorder] Saved clip: {filepath} ({len(self.current_frames)} frames)")
        
        # Reset state
        self.recording = False
        self.current_frames = []
        self.current_alert = None
        
        return str(filepath)
    
    @property
    def is_recording(self) -> bool:
        return self.recording
