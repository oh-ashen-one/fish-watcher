"""
Rolling buffer for storing recent frames.
Allows capturing footage from BEFORE a trigger event.
"""

import collections
import threading
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class BufferedFrame:
    """A single frame with metadata."""
    frame: np.ndarray
    timestamp: float
    frame_number: int


class RollingBuffer:
    """Thread-safe rolling buffer for video frames."""
    
    def __init__(self, max_seconds: float = 10, fps: int = 15):
        self.max_frames = int(max_seconds * fps)
        self.fps = fps
        self.buffer: collections.deque[BufferedFrame] = collections.deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        self.frame_count = 0
    
    def add(self, frame: np.ndarray) -> None:
        """Add a frame to the buffer."""
        with self.lock:
            buffered = BufferedFrame(
                frame=frame.copy(),
                timestamp=time.time(),
                frame_number=self.frame_count
            )
            self.buffer.append(buffered)
            self.frame_count += 1
    
    def get_all(self) -> list[BufferedFrame]:
        """Get all frames in buffer (oldest first)."""
        with self.lock:
            return list(self.buffer)
    
    def get_recent(self, seconds: float) -> list[BufferedFrame]:
        """Get frames from the last N seconds."""
        cutoff = time.time() - seconds
        with self.lock:
            return [f for f in self.buffer if f.timestamp >= cutoff]
    
    def clear(self) -> None:
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()
    
    @property
    def duration(self) -> float:
        """Current buffer duration in seconds."""
        with self.lock:
            if len(self.buffer) < 2:
                return 0
            return self.buffer[-1].timestamp - self.buffer[0].timestamp
    
    def __len__(self) -> int:
        return len(self.buffer)
