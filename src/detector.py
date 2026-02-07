"""
Detection algorithms for fish tank monitoring.
Full feature set - all detectors.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from collections import deque
import numpy as np
import cv2


class AlertType(Enum):
    # Health/Emergency
    NO_MOTION = "no_motion"
    MOTION_SPIKE = "motion_spike"
    FISH_FLOATING = "fish_floating"
    FISH_BOTTOM = "fish_stuck_bottom"
    ERRATIC_SWIMMING = "erratic_swimming"
    GASPING_SURFACE = "gasping_surface"
    AGGRESSION = "fish_aggression"
    
    # Tank Issues
    COLOR_CHANGE = "color_change"
    WATER_CLOUDY = "water_cloudy"
    ALGAE_GROWTH = "algae_growth"
    WATER_LEVEL_DROP = "water_level_drop"
    FILTER_STOPPED = "filter_stopped"
    LIGHT_STUCK = "light_stuck"
    
    # Behavior
    SURFACE_ACTIVITY = "surface_activity"
    HIDING_TOO_LONG = "hiding_too_long"
    MISSED_FEEDING = "missed_feeding"
    CLUSTERING = "fish_clustering"
    LOW_ACTIVITY = "low_activity"
    
    # Cool Moments
    INTERESTING_MOMENT = "interesting_moment"
    FEEDING_FRENZY = "feeding_frenzy"
    FISH_PLAYING = "fish_playing"
    NEW_BEHAVIOR = "new_behavior"


@dataclass
class Alert:
    """Represents a detected alert."""
    type: AlertType
    message: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    frame: Optional[np.ndarray] = None
    is_cool_moment: bool = False  # True = good, False = potential problem


@dataclass 
class DetectorConfig:
    """Configuration for detectors."""
    motion_sensitivity: int = 50
    no_motion_threshold: int = 300  # 5 min
    color_change_threshold: int = 15
    surface_zone_percent: int = 15
    bottom_zone_percent: int = 15
    learn_baseline: bool = True
    feeding_times: list = field(default_factory=list)  # ["09:00", "18:00"]
    fish_count: int = 0  # 0 = auto-detect


class MotionDetector:
    """Detects motion and no-motion events."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.prev_frame: Optional[np.ndarray] = None
        self.last_motion_time: float = time.time()
        self.motion_history: deque = deque(maxlen=1000)
        self.baseline_motion: Optional[float] = None
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process a frame and return alerts if triggered."""
        alerts = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return alerts
        
        # Calculate frame difference
        delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        motion_level = np.sum(thresh) / thresh.size / 255 * 100
        
        self.prev_frame = gray
        self.motion_history.append(motion_level)
        
        # Update baseline
        if self.config.learn_baseline and len(self.motion_history) > 100:
            self.baseline_motion = np.mean(list(self.motion_history))
        
        # Check for motion
        sensitivity_threshold = (100 - self.config.motion_sensitivity) / 10
        
        if motion_level > sensitivity_threshold:
            self.last_motion_time = time.time()
            
            # Check for motion spike (potential erratic behavior)
            if self.baseline_motion and motion_level > self.baseline_motion * 3:
                alerts.append(Alert(
                    type=AlertType.MOTION_SPIKE,
                    message=f"Unusual activity spike! Motion: {motion_level:.1f}%",
                    confidence=min(motion_level / 20, 1.0),
                    frame=frame
                ))
            
            # Extreme spike = erratic swimming
            if self.baseline_motion and motion_level > self.baseline_motion * 5:
                alerts.append(Alert(
                    type=AlertType.ERRATIC_SWIMMING,
                    message=f"Possible erratic swimming detected! Motion: {motion_level:.1f}%",
                    confidence=min(motion_level / 30, 1.0),
                    frame=frame
                ))
        
        # Check for no motion
        no_motion_duration = time.time() - self.last_motion_time
        if no_motion_duration > self.config.no_motion_threshold:
            alerts.append(Alert(
                type=AlertType.NO_MOTION,
                message=f"No motion for {int(no_motion_duration)} seconds",
                confidence=min(no_motion_duration / self.config.no_motion_threshold, 1.0),
                frame=frame
            ))
        
        # Check for low activity (sustained below baseline)
        if self.baseline_motion and len(self.motion_history) > 100:
            recent_avg = np.mean(list(self.motion_history)[-100:])
            if recent_avg < self.baseline_motion * 0.3:
                alerts.append(Alert(
                    type=AlertType.LOW_ACTIVITY,
                    message="Activity levels significantly below normal",
                    confidence=0.6,
                    frame=frame
                ))
        
        return alerts


class ColorDetector:
    """Detects water color changes (cloudiness, algae)."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.baseline_color: Optional[np.ndarray] = None
        self.baseline_hsv: Optional[np.ndarray] = None
        self.color_samples: deque = deque(maxlen=500)
        self.green_history: deque = deque(maxlen=500)
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process a frame and check for color changes."""
        alerts = []
        h, w = frame.shape[:2]
        center = frame[h//4:3*h//4, w//4:3*w//4]
        
        # BGR average
        avg_color = np.mean(center, axis=(0, 1))
        self.color_samples.append(avg_color)
        
        # HSV for algae detection (green tint)
        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
        avg_hsv = np.mean(hsv, axis=(0, 1))
        green_level = avg_hsv[0]  # Hue channel
        self.green_history.append(green_level)
        
        # Establish baselines
        if self.baseline_color is None and len(self.color_samples) >= 100:
            self.baseline_color = np.mean(list(self.color_samples)[:100], axis=0)
            self.baseline_hsv = np.mean(list(self.green_history)[:100])
        
        if self.baseline_color is None:
            return alerts
        
        # Color difference (cloudiness)
        color_diff = np.linalg.norm(avg_color - self.baseline_color)
        
        if color_diff > self.config.color_change_threshold:
            # Check if it's getting whiter/grayer (cloudy)
            brightness_change = np.mean(avg_color) - np.mean(self.baseline_color)
            
            if brightness_change > 10:
                alerts.append(Alert(
                    type=AlertType.WATER_CLOUDY,
                    message=f"Water appears cloudy. Color shift: {color_diff:.1f}",
                    confidence=min(color_diff / 30, 1.0),
                    frame=frame
                ))
            else:
                alerts.append(Alert(
                    type=AlertType.COLOR_CHANGE,
                    message=f"Water color changed. Difference: {color_diff:.1f}",
                    confidence=min(color_diff / 30, 1.0),
                    frame=frame
                ))
        
        # Algae detection (green shift)
        if self.baseline_hsv and len(self.green_history) > 100:
            recent_green = np.mean(list(self.green_history)[-50:])
            green_shift = recent_green - self.baseline_hsv
            
            # Green hue is around 60 in OpenCV HSV
            if 40 < recent_green < 80 and green_shift > 10:
                alerts.append(Alert(
                    type=AlertType.ALGAE_GROWTH,
                    message="Possible algae growth - green tint increasing",
                    confidence=min(green_shift / 20, 1.0),
                    frame=frame
                ))
        
        return alerts


class ZoneDetector:
    """Detects activity in specific zones (surface, bottom, corners)."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.surface_activity_start: Optional[float] = None
        self.bottom_activity_start: Optional[float] = None
        self.corner_activity: dict = {}
        self.hiding_start: Optional[float] = None
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Check for zone-specific activity."""
        alerts = []
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Define zones
        surface_h = int(h * self.config.surface_zone_percent / 100)
        bottom_h = int(h * self.config.bottom_zone_percent / 100)
        
        surface_zone = gray[:surface_h, :]
        bottom_zone = gray[-bottom_h:, :]
        
        # Detect bright spots (fish) in zones
        surface_activity = np.sum(surface_zone > 180) / surface_zone.size * 100
        bottom_activity = np.sum(bottom_zone > 180) / bottom_zone.size * 100
        
        # Surface activity (gasping/floating)
        if surface_activity > 5:
            if self.surface_activity_start is None:
                self.surface_activity_start = time.time()
            elif time.time() - self.surface_activity_start > 60:  # 1 min sustained
                alerts.append(Alert(
                    type=AlertType.GASPING_SURFACE,
                    message="Fish at surface for extended period - possible oxygen issue",
                    confidence=0.7,
                    frame=frame
                ))
            elif time.time() - self.surface_activity_start > 30:
                alerts.append(Alert(
                    type=AlertType.SURFACE_ACTIVITY,
                    message="Sustained activity at water surface",
                    confidence=0.6,
                    frame=frame
                ))
        else:
            self.surface_activity_start = None
        
        # Bottom activity (stuck/sick fish)
        if bottom_activity > 8:
            if self.bottom_activity_start is None:
                self.bottom_activity_start = time.time()
            elif time.time() - self.bottom_activity_start > 300:  # 5 min
                alerts.append(Alert(
                    type=AlertType.FISH_BOTTOM,
                    message="Fish stuck at bottom for extended period",
                    confidence=0.7,
                    frame=frame
                ))
        else:
            self.bottom_activity_start = None
        
        # Corner clustering (stress)
        corners = [
            gray[:h//3, :w//3],      # top-left
            gray[:h//3, -w//3:],     # top-right
            gray[-h//3:, :w//3],     # bottom-left
            gray[-h//3:, -w//3:],    # bottom-right
        ]
        
        corner_activities = [np.sum(c > 180) / c.size * 100 for c in corners]
        max_corner_activity = max(corner_activities)
        
        if max_corner_activity > 15:  # Lots of activity in one corner
            total_activity = sum(corner_activities)
            if max_corner_activity / total_activity > 0.7:  # 70%+ in one corner
                alerts.append(Alert(
                    type=AlertType.CLUSTERING,
                    message="Fish clustering in corner - possible stress",
                    confidence=0.6,
                    frame=frame
                ))
        
        return alerts


class FishCountDetector:
    """Attempts to count fish and detect changes."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.count_history: deque = deque(maxlen=100)
        self.baseline_count: Optional[int] = None
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Count fish-like objects in frame."""
        alerts = []
        
        # Convert to grayscale and threshold
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        
        # Adaptive threshold to find fish-shaped blobs
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size (fish-sized objects)
        h, w = frame.shape[:2]
        min_area = (h * w) * 0.001  # 0.1% of frame
        max_area = (h * w) * 0.1    # 10% of frame
        
        fish_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                fish_count += 1
        
        self.count_history.append(fish_count)
        
        # Establish baseline
        if self.baseline_count is None and len(self.count_history) >= 50:
            self.baseline_count = int(np.median(list(self.count_history)))
            if self.config.fish_count == 0:
                print(f"[FishCount] Auto-detected baseline: {self.baseline_count} fish")
        
        # Check for missing fish
        if self.baseline_count and len(self.count_history) >= 10:
            recent_count = int(np.median(list(self.count_history)[-10:]))
            expected = self.config.fish_count if self.config.fish_count > 0 else self.baseline_count
            
            if recent_count < expected - 1:  # One or more missing
                alerts.append(Alert(
                    type=AlertType.NO_MOTION,  # Reusing for "fish missing"
                    message=f"Fish count dropped: seeing {recent_count}, expected {expected}",
                    confidence=0.5,
                    frame=frame
                ))
        
        return alerts


class FilterDetector:
    """Detects if filter/bubbles have stopped."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.bubble_history: deque = deque(maxlen=300)
        self.baseline_bubbles: Optional[float] = None
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Detect bubble/water movement patterns."""
        alerts = []
        
        # Focus on areas where filter output usually is (top corners)
        h, w = frame.shape[:2]
        filter_zones = [
            frame[:h//4, :w//4],      # top-left
            frame[:h//4, -w//4:],     # top-right
        ]
        
        # Detect small rapid movements (bubbles)
        total_bubble_activity = 0
        for zone in filter_zones:
            gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
            # High-pass filter to detect small movements
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            bubble_activity = np.var(laplacian)
            total_bubble_activity += bubble_activity
        
        self.bubble_history.append(total_bubble_activity)
        
        # Establish baseline
        if self.baseline_bubbles is None and len(self.bubble_history) >= 100:
            self.baseline_bubbles = np.mean(list(self.bubble_history))
        
        # Check for filter stopped
        if self.baseline_bubbles and len(self.bubble_history) >= 60:
            recent_activity = np.mean(list(self.bubble_history)[-60:])
            
            if recent_activity < self.baseline_bubbles * 0.2:
                alerts.append(Alert(
                    type=AlertType.FILTER_STOPPED,
                    message="Filter/bubbles may have stopped - check equipment",
                    confidence=0.6,
                    frame=frame
                ))
        
        return alerts


class CoolMomentDetector:
    """Detects interesting/cool moments worth clipping."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.activity_history: deque = deque(maxlen=100)
        self.baseline_activity: Optional[float] = None
        self.last_cool_moment: float = 0
        self.cooldown = 300  # 5 min between cool clips
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Detect interesting moments."""
        alerts = []
        
        if time.time() - self.last_cool_moment < self.cooldown:
            return alerts
        
        # Calculate overall activity
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        activity = np.std(gray)
        self.activity_history.append(activity)
        
        if self.baseline_activity is None and len(self.activity_history) >= 50:
            self.baseline_activity = np.mean(list(self.activity_history))
        
        if self.baseline_activity is None:
            return alerts
        
        # Feeding frenzy detection (high sustained activity)
        if len(self.activity_history) >= 10:
            recent = np.mean(list(self.activity_history)[-10:])
            
            if recent > self.baseline_activity * 2:
                alerts.append(Alert(
                    type=AlertType.FEEDING_FRENZY,
                    message="High activity - possible feeding frenzy!",
                    confidence=0.7,
                    frame=frame,
                    is_cool_moment=True
                ))
                self.last_cool_moment = time.time()
            
            # Interesting spike
            elif recent > self.baseline_activity * 1.5:
                alerts.append(Alert(
                    type=AlertType.INTERESTING_MOMENT,
                    message="Interesting activity spike",
                    confidence=0.5,
                    frame=frame,
                    is_cool_moment=True
                ))
                self.last_cool_moment = time.time()
        
        return alerts


class FishWatcherDetector:
    """Main detector combining all detection methods."""
    
    def __init__(self, config: DetectorConfig):
        self.config = config
        self.detectors = [
            MotionDetector(config),
            ColorDetector(config),
            ZoneDetector(config),
            FishCountDetector(config),
            FilterDetector(config),
            CoolMomentDetector(config),
        ]
        self.last_alert_time: dict[AlertType, float] = {}
        self.cooldown = 60  # seconds
        
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process frame through all detectors."""
        all_alerts = []
        
        for detector in self.detectors:
            try:
                alerts = detector.process(frame)
                for alert in alerts:
                    if self._check_cooldown(alert.type):
                        all_alerts.append(alert)
                        self.last_alert_time[alert.type] = time.time()
            except Exception as e:
                print(f"[Detector] Error in {detector.__class__.__name__}: {e}")
        
        return all_alerts
    
    def _check_cooldown(self, alert_type: AlertType) -> bool:
        """Check if enough time has passed since last alert of this type."""
        last_time = self.last_alert_time.get(alert_type, 0)
        return time.time() - last_time > self.cooldown
