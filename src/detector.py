"""
Detection algorithms for fish tank monitoring.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np
import cv2


class AlertType(Enum):
    NO_MOTION = "no_motion"
    MOTION_SPIKE = "motion_spike"
    COLOR_CHANGE = "color_change"
    SURFACE_ACTIVITY = "surface_activity"
    UNUSUAL_PATTERN = "unusual_pattern"
    INTERESTING_MOMENT = "interesting_moment"


@dataclass
class Alert:
    """Represents a detected alert."""
    type: AlertType
    message: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    frame: Optional[np.ndarray] = None


@dataclass 
class DetectorConfig:
    """Configuration for detectors."""
    motion_sensitivity: int = 50
    no_motion_threshold: int = 300
    color_change_threshold: int = 15
    surface_zone_percent: int = 15
    learn_baseline: bool = True


class MotionDetector:
    """Detects motion and no-motion events."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.prev_frame: Optional[np.ndarray] = None
        self.last_motion_time: float = time.time()
        self.motion_history: list[float] = []
        self.baseline_motion: Optional[float] = None
        
    def process(self, frame: np.ndarray) -> Optional[Alert]:
        """Process a frame and return an alert if triggered."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        # Calculate frame difference
        delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        motion_level = np.sum(thresh) / thresh.size / 255 * 100
        
        self.prev_frame = gray
        
        # Update motion history
        self.motion_history.append(motion_level)
        if len(self.motion_history) > 1000:
            self.motion_history = self.motion_history[-500:]
        
        # Update baseline
        if self.config.learn_baseline and len(self.motion_history) > 100:
            self.baseline_motion = np.mean(self.motion_history)
        
        # Check for motion
        sensitivity_threshold = (100 - self.config.motion_sensitivity) / 10
        
        if motion_level > sensitivity_threshold:
            self.last_motion_time = time.time()
            
            # Check for motion spike
            if self.baseline_motion and motion_level > self.baseline_motion * 3:
                return Alert(
                    type=AlertType.MOTION_SPIKE,
                    message=f"Unusual activity spike detected! Motion level: {motion_level:.1f}%",
                    confidence=min(motion_level / 20, 1.0),
                    frame=frame
                )
        
        # Check for no motion
        no_motion_duration = time.time() - self.last_motion_time
        if no_motion_duration > self.config.no_motion_threshold:
            return Alert(
                type=AlertType.NO_MOTION,
                message=f"No motion detected for {int(no_motion_duration)} seconds",
                confidence=min(no_motion_duration / self.config.no_motion_threshold, 1.0),
                frame=frame
            )
        
        return None


class ColorDetector:
    """Detects water color changes (cloudiness, algae)."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.baseline_color: Optional[np.ndarray] = None
        self.color_samples: list[np.ndarray] = []
        
    def process(self, frame: np.ndarray) -> Optional[Alert]:
        """Process a frame and check for color changes."""
        # Sample center region (avoid edges)
        h, w = frame.shape[:2]
        center = frame[h//4:3*h//4, w//4:3*w//4]
        avg_color = np.mean(center, axis=(0, 1))
        
        self.color_samples.append(avg_color)
        if len(self.color_samples) > 100:
            self.color_samples = self.color_samples[-50:]
        
        # Establish baseline
        if self.baseline_color is None and len(self.color_samples) >= 50:
            self.baseline_color = np.mean(self.color_samples[:50], axis=0)
        
        if self.baseline_color is None:
            return None
        
        # Calculate color difference
        color_diff = np.linalg.norm(avg_color - self.baseline_color)
        
        if color_diff > self.config.color_change_threshold:
            return Alert(
                type=AlertType.COLOR_CHANGE,
                message=f"Water color change detected! Difference: {color_diff:.1f}",
                confidence=min(color_diff / 30, 1.0),
                frame=frame
            )
        
        return None


class SurfaceDetector:
    """Detects activity in the surface zone (floating fish)."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.surface_activity_start: Optional[float] = None
        
    def process(self, frame: np.ndarray) -> Optional[Alert]:
        """Check for sustained activity at water surface."""
        h, w = frame.shape[:2]
        surface_height = int(h * self.config.surface_zone_percent / 100)
        surface_zone = frame[:surface_height, :]
        
        # Convert to grayscale and detect movement
        gray = cv2.cvtColor(surface_zone, cv2.COLOR_BGR2GRAY)
        
        # Simple brightness check (fish at surface = lighter pixels)
        bright_pixels = np.sum(gray > 200) / gray.size * 100
        
        if bright_pixels > 5:  # Significant activity at surface
            if self.surface_activity_start is None:
                self.surface_activity_start = time.time()
            elif time.time() - self.surface_activity_start > 30:  # 30 sec sustained
                return Alert(
                    type=AlertType.SURFACE_ACTIVITY,
                    message="Sustained activity at water surface - possible fish in distress",
                    confidence=0.7,
                    frame=frame
                )
        else:
            self.surface_activity_start = None
        
        return None


class FishWatcherDetector:
    """Main detector combining all detection methods."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.motion = MotionDetector(config)
        self.color = ColorDetector(config)
        self.surface = SurfaceDetector(config)
        self.last_alert_time: dict[AlertType, float] = {}
        self.cooldown = 60  # seconds
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process frame through all detectors."""
        alerts = []
        
        # Run all detectors
        for detector in [self.motion, self.color, self.surface]:
            alert = detector.process(frame)
            if alert and self._check_cooldown(alert.type):
                alerts.append(alert)
                self.last_alert_time[alert.type] = time.time()
        
        return alerts
    
    def _check_cooldown(self, alert_type: AlertType) -> bool:
        """Check if enough time has passed since last alert of this type."""
        last_time = self.last_alert_time.get(alert_type, 0)
        return time.time() - last_time > self.cooldown
