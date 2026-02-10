"""
Detection algorithms for fish tank monitoring.
Full feature set - all detectors.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from collections import deque
import numpy as np
import cv2

logger = logging.getLogger(__name__)


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


class BaseDetector(ABC):
    """Abstract base class for all detectors."""

    def __init__(self, config: DetectorConfig) -> None:
        self.config = config

    @abstractmethod
    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process a frame and return any triggered alerts."""
        ...


class MotionDetector(BaseDetector):
    """Detects motion and no-motion events."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.prev_frame: Optional[np.ndarray] = None
        self.last_motion_time: float = time.time()
        self.motion_history: deque = deque(maxlen=1000)
        self.baseline_motion: Optional[float] = None

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process a frame and return alerts if triggered."""
        alerts: list[Alert] = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            return alerts

        motion_level = self._compute_motion_level(gray)
        self.prev_frame = gray
        self.motion_history.append(motion_level)
        self._update_baseline()

        sensitivity_threshold = (100 - self.config.motion_sensitivity) / 10

        if motion_level > sensitivity_threshold:
            self.last_motion_time = time.time()
            alerts.extend(self._check_motion_spikes(motion_level, frame))

        alerts.extend(self._check_no_motion(frame))
        alerts.extend(self._check_low_activity(frame))

        return alerts

    def _compute_motion_level(self, gray: np.ndarray) -> float:
        """Compute motion level as percentage of changed pixels."""
        delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        return float(np.sum(thresh) / thresh.size / 255 * 100)

    def _update_baseline(self) -> None:
        """Update baseline motion from history."""
        if self.config.learn_baseline and len(self.motion_history) > 100:
            self.baseline_motion = float(np.mean(list(self.motion_history)))

    def _check_motion_spikes(self, motion_level: float, frame: np.ndarray) -> list[Alert]:
        """Check for unusual motion spikes and erratic swimming."""
        alerts: list[Alert] = []
        if not self.baseline_motion:
            return alerts

        if motion_level > self.baseline_motion * 5:
            alerts.append(Alert(
                type=AlertType.ERRATIC_SWIMMING,
                message=f"Possible erratic swimming detected! Motion: {motion_level:.1f}%",
                confidence=min(motion_level / 30, 1.0),
                frame=frame,
            ))
        elif motion_level > self.baseline_motion * 3:
            alerts.append(Alert(
                type=AlertType.MOTION_SPIKE,
                message=f"Unusual activity spike! Motion: {motion_level:.1f}%",
                confidence=min(motion_level / 20, 1.0),
                frame=frame,
            ))

        return alerts

    def _check_no_motion(self, frame: np.ndarray) -> list[Alert]:
        """Check for extended period of no motion."""
        no_motion_duration = time.time() - self.last_motion_time
        if no_motion_duration > self.config.no_motion_threshold:
            return [Alert(
                type=AlertType.NO_MOTION,
                message=f"No motion for {int(no_motion_duration)} seconds",
                confidence=min(no_motion_duration / self.config.no_motion_threshold, 1.0),
                frame=frame,
            )]
        return []

    def _check_low_activity(self, frame: np.ndarray) -> list[Alert]:
        """Check for sustained below-baseline activity."""
        if not self.baseline_motion or len(self.motion_history) <= 100:
            return []
        recent_avg = float(np.mean(list(self.motion_history)[-100:]))
        if recent_avg < self.baseline_motion * 0.3:
            return [Alert(
                type=AlertType.LOW_ACTIVITY,
                message="Activity levels significantly below normal",
                confidence=0.6,
                frame=frame,
            )]
        return []


class ColorDetector(BaseDetector):
    """Detects water color changes (cloudiness, algae)."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.baseline_color: Optional[np.ndarray] = None
        self.baseline_hsv: Optional[float] = None
        self.color_samples: deque = deque(maxlen=500)
        self.green_history: deque = deque(maxlen=500)

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Process a frame and check for color changes."""
        alerts: list[Alert] = []
        center = self._extract_center_region(frame)

        avg_color, green_level = self._compute_color_stats(center)
        self.color_samples.append(avg_color)
        self.green_history.append(green_level)

        self._establish_baselines()
        if self.baseline_color is None:
            return alerts

        alerts.extend(self._check_color_change(avg_color, frame))
        alerts.extend(self._check_algae_growth(frame))

        return alerts

    def _extract_center_region(self, frame: np.ndarray) -> np.ndarray:
        """Extract the center quarter of the frame."""
        h, w = frame.shape[:2]
        return frame[h // 4:3 * h // 4, w // 4:3 * w // 4]

    def _compute_color_stats(self, region: np.ndarray) -> tuple[np.ndarray, float]:
        """Compute average BGR color and green hue level."""
        avg_color = np.mean(region, axis=(0, 1))
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        avg_hsv = np.mean(hsv, axis=(0, 1))
        return avg_color, float(avg_hsv[0])

    def _establish_baselines(self) -> None:
        """Establish color baselines from initial samples."""
        if self.baseline_color is None and len(self.color_samples) >= 100:
            self.baseline_color = np.mean(list(self.color_samples)[:100], axis=0)
            self.baseline_hsv = float(np.mean(list(self.green_history)[:100]))

    def _check_color_change(self, avg_color: np.ndarray, frame: np.ndarray) -> list[Alert]:
        """Check for water color change / cloudiness."""
        color_diff = float(np.linalg.norm(avg_color - self.baseline_color))
        if color_diff <= self.config.color_change_threshold:
            return []

        brightness_change = float(np.mean(avg_color) - np.mean(self.baseline_color))
        if brightness_change > 10:
            return [Alert(
                type=AlertType.WATER_CLOUDY,
                message=f"Water appears cloudy. Color shift: {color_diff:.1f}",
                confidence=min(color_diff / 30, 1.0),
                frame=frame,
            )]
        return [Alert(
            type=AlertType.COLOR_CHANGE,
            message=f"Water color changed. Difference: {color_diff:.1f}",
            confidence=min(color_diff / 30, 1.0),
            frame=frame,
        )]

    def _check_algae_growth(self, frame: np.ndarray) -> list[Alert]:
        """Check for green tint increase (algae)."""
        if not self.baseline_hsv or len(self.green_history) <= 100:
            return []
        recent_green = float(np.mean(list(self.green_history)[-50:]))
        green_shift = recent_green - self.baseline_hsv
        if 40 < recent_green < 80 and green_shift > 10:
            return [Alert(
                type=AlertType.ALGAE_GROWTH,
                message="Possible algae growth - green tint increasing",
                confidence=min(green_shift / 20, 1.0),
                frame=frame,
            )]
        return []


class ZoneDetector(BaseDetector):
    """Detects activity in specific zones (surface, bottom, corners)."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.surface_activity_start: Optional[float] = None
        self.bottom_activity_start: Optional[float] = None
        self.corner_activity: dict = {}
        self.hiding_start: Optional[float] = None

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Check for zone-specific activity."""
        alerts: list[Alert] = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        alerts.extend(self._check_surface_activity(gray, frame))
        alerts.extend(self._check_bottom_activity(gray, frame))
        alerts.extend(self._check_corner_clustering(gray, frame))

        return alerts

    def _get_zone_activity(self, zone: np.ndarray, brightness_threshold: int = 180) -> float:
        """Calculate percentage of bright pixels in a zone."""
        return float(np.sum(zone > brightness_threshold) / zone.size * 100)

    def _check_surface_activity(self, gray: np.ndarray, frame: np.ndarray) -> list[Alert]:
        """Check for fish at the surface (gasping/floating)."""
        h, w = gray.shape[:2]
        surface_h = int(h * self.config.surface_zone_percent / 100)
        surface_zone = gray[:surface_h, :]
        surface_activity = self._get_zone_activity(surface_zone)

        alerts: list[Alert] = []
        if surface_activity > 5:
            if self.surface_activity_start is None:
                self.surface_activity_start = time.time()
            else:
                duration = time.time() - self.surface_activity_start
                if duration > 60:
                    alerts.append(Alert(
                        type=AlertType.GASPING_SURFACE,
                        message="Fish at surface for extended period - possible oxygen issue",
                        confidence=0.7, frame=frame,
                    ))
                elif duration > 30:
                    alerts.append(Alert(
                        type=AlertType.SURFACE_ACTIVITY,
                        message="Sustained activity at water surface",
                        confidence=0.6, frame=frame,
                    ))
        else:
            self.surface_activity_start = None
        return alerts

    def _check_bottom_activity(self, gray: np.ndarray, frame: np.ndarray) -> list[Alert]:
        """Check for fish stuck at the bottom."""
        h, w = gray.shape[:2]
        bottom_h = int(h * self.config.bottom_zone_percent / 100)
        bottom_zone = gray[-bottom_h:, :]
        bottom_activity = self._get_zone_activity(bottom_zone)

        alerts: list[Alert] = []
        if bottom_activity > 8:
            if self.bottom_activity_start is None:
                self.bottom_activity_start = time.time()
            elif time.time() - self.bottom_activity_start > 300:
                alerts.append(Alert(
                    type=AlertType.FISH_BOTTOM,
                    message="Fish stuck at bottom for extended period",
                    confidence=0.7, frame=frame,
                ))
        else:
            self.bottom_activity_start = None
        return alerts

    def _check_corner_clustering(self, gray: np.ndarray, frame: np.ndarray) -> list[Alert]:
        """Check for fish clustering in a single corner."""
        h, w = gray.shape[:2]
        corners = [
            gray[:h // 3, :w // 3],
            gray[:h // 3, -w // 3:],
            gray[-h // 3:, :w // 3],
            gray[-h // 3:, -w // 3:],
        ]
        corner_activities = [self._get_zone_activity(c) for c in corners]
        max_corner = max(corner_activities)
        total = sum(corner_activities)

        if max_corner > 15 and total > 0 and max_corner / total > 0.7:
            return [Alert(
                type=AlertType.CLUSTERING,
                message="Fish clustering in corner - possible stress",
                confidence=0.6, frame=frame,
            )]
        return []


class FishCountDetector(BaseDetector):
    """Attempts to count fish and detect changes."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.count_history: deque = deque(maxlen=100)
        self.baseline_count: Optional[int] = None

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Count fish-like objects in frame."""
        fish_count = self._count_fish_objects(frame)
        self.count_history.append(fish_count)
        self._establish_baseline()
        return self._check_missing_fish(frame)

    def _count_fish_objects(self, frame: np.ndarray) -> int:
        """Count fish-sized contours in the frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2,
        )
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = frame.shape[:2]
        min_area = (h * w) * 0.001
        max_area = (h * w) * 0.1
        return sum(1 for c in contours if min_area < cv2.contourArea(c) < max_area)

    def _establish_baseline(self) -> None:
        """Establish baseline fish count from history."""
        if self.baseline_count is None and len(self.count_history) >= 50:
            self.baseline_count = int(np.median(list(self.count_history)))
            if self.config.fish_count == 0:
                logger.info(f"Auto-detected baseline: {self.baseline_count} fish")

    def _check_missing_fish(self, frame: np.ndarray) -> list[Alert]:
        """Check if current count is below expected."""
        if not self.baseline_count or len(self.count_history) < 10:
            return []
        recent_count = int(np.median(list(self.count_history)[-10:]))
        expected = self.config.fish_count if self.config.fish_count > 0 else self.baseline_count
        if recent_count < expected - 1:
            return [Alert(
                type=AlertType.NO_MOTION,
                message=f"Fish count dropped: seeing {recent_count}, expected {expected}",
                confidence=0.5, frame=frame,
            )]
        return []


class FilterDetector(BaseDetector):
    """Detects if filter/bubbles have stopped."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.bubble_history: deque = deque(maxlen=300)
        self.baseline_bubbles: Optional[float] = None

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Detect bubble/water movement patterns."""
        bubble_activity = self._measure_bubble_activity(frame)
        self.bubble_history.append(bubble_activity)
        self._establish_baseline()
        return self._check_filter_stopped(frame)

    def _measure_bubble_activity(self, frame: np.ndarray) -> float:
        """Measure bubble activity in filter zones (top corners)."""
        h, w = frame.shape[:2]
        filter_zones = [
            frame[:h // 4, :w // 4],
            frame[:h // 4, -w // 4:],
        ]
        total = 0.0
        for zone in filter_zones:
            gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            total += float(np.var(laplacian))
        return total

    def _establish_baseline(self) -> None:
        """Establish bubble activity baseline."""
        if self.baseline_bubbles is None and len(self.bubble_history) >= 100:
            self.baseline_bubbles = float(np.mean(list(self.bubble_history)))

    def _check_filter_stopped(self, frame: np.ndarray) -> list[Alert]:
        """Check if filter activity has dropped significantly."""
        if not self.baseline_bubbles or len(self.bubble_history) < 60:
            return []
        recent = float(np.mean(list(self.bubble_history)[-60:]))
        if recent < self.baseline_bubbles * 0.2:
            return [Alert(
                type=AlertType.FILTER_STOPPED,
                message="Filter/bubbles may have stopped - check equipment",
                confidence=0.6, frame=frame,
            )]
        return []


class CoolMomentDetector(BaseDetector):
    """Detects interesting/cool moments worth clipping."""

    def __init__(self, config: DetectorConfig) -> None:
        super().__init__(config)
        self.activity_history: deque = deque(maxlen=100)
        self.baseline_activity: Optional[float] = None
        self.last_cool_moment: float = 0
        self.cooldown = 300  # 5 min between cool clips

    def process(self, frame: np.ndarray) -> list[Alert]:
        """Detect interesting moments."""
        if time.time() - self.last_cool_moment < self.cooldown:
            return []

        activity = self._compute_activity(frame)
        self.activity_history.append(activity)
        self._establish_baseline()

        if self.baseline_activity is None:
            return []

        return self._check_interesting_activity(frame)

    def _compute_activity(self, frame: np.ndarray) -> float:
        """Compute activity metric from frame variance."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.std(gray))

    def _establish_baseline(self) -> None:
        """Establish activity baseline."""
        if self.baseline_activity is None and len(self.activity_history) >= 50:
            self.baseline_activity = float(np.mean(list(self.activity_history)))

    def _check_interesting_activity(self, frame: np.ndarray) -> list[Alert]:
        """Check for feeding frenzy or interesting moment."""
        if len(self.activity_history) < 10:
            return []
        recent = float(np.mean(list(self.activity_history)[-10:]))

        if recent > self.baseline_activity * 2:
            self.last_cool_moment = time.time()
            return [Alert(
                type=AlertType.FEEDING_FRENZY,
                message="High activity - possible feeding frenzy!",
                confidence=0.7, frame=frame, is_cool_moment=True,
            )]
        elif recent > self.baseline_activity * 1.5:
            self.last_cool_moment = time.time()
            return [Alert(
                type=AlertType.INTERESTING_MOMENT,
                message="Interesting activity spike",
                confidence=0.5, frame=frame, is_cool_moment=True,
            )]
        return []


class FishWatcherDetector:
    """Main detector combining all detection methods."""

    def __init__(self, config: DetectorConfig) -> None:
        self.config = config
        self.detectors: list[BaseDetector] = [
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
        all_alerts: list[Alert] = []

        for detector in self.detectors:
            try:
                alerts = detector.process(frame)
                for alert in alerts:
                    if self._check_cooldown(alert.type):
                        all_alerts.append(alert)
                        self.last_alert_time[alert.type] = time.time()
            except Exception as e:
                logger.error(f"Error in {detector.__class__.__name__}: {e}")

        return all_alerts

    def _check_cooldown(self, alert_type: AlertType) -> bool:
        """Check if enough time has passed since last alert of this type."""
        last_time = self.last_alert_time.get(alert_type, 0)
        return time.time() - last_time > self.cooldown
