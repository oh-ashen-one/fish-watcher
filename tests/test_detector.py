"""Tests for src.detector — core detection logic."""

import time
import numpy as np
import pytest

from src.detector import (
    Alert,
    AlertType,
    BaseDetector,
    ColorDetector,
    CoolMomentDetector,
    DetectorConfig,
    FilterDetector,
    FishCountDetector,
    FishWatcherDetector,
    MotionDetector,
    ZoneDetector,
)


# ---------------------------------------------------------------------------
# BaseDetector
# ---------------------------------------------------------------------------

class TestBaseDetector:
    def test_cannot_instantiate(self, default_config: DetectorConfig) -> None:
        """BaseDetector is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDetector(default_config)  # type: ignore[abstract]

    def test_subclass_must_implement_process(self, default_config: DetectorConfig) -> None:
        class Incomplete(BaseDetector):
            pass

        with pytest.raises(TypeError):
            Incomplete(default_config)  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# MotionDetector
# ---------------------------------------------------------------------------

class TestMotionDetector:
    def test_first_frame_returns_no_alerts(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = MotionDetector(default_config)
        alerts = det.process(blank_frame)
        assert alerts == []

    def test_identical_frames_no_alerts(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = MotionDetector(default_config)
        det.process(blank_frame)
        alerts = det.process(blank_frame.copy())
        # No motion between identical frames
        # (no_motion alert won't fire immediately — needs to exceed threshold)
        motion_types = {a.type for a in alerts}
        assert AlertType.MOTION_SPIKE not in motion_types
        assert AlertType.ERRATIC_SWIMMING not in motion_types

    def test_motion_spike_detected(self, default_config: DetectorConfig) -> None:
        det = MotionDetector(default_config)
        # Build baseline with 150 blank frames
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(150):
            det.process(blank)

        # Introduce a massive change
        bright = np.full((480, 640, 3), 255, dtype=np.uint8)
        alerts = det.process(bright)
        types = {a.type for a in alerts}
        assert AlertType.MOTION_SPIKE in types or AlertType.ERRATIC_SWIMMING in types

    def test_compute_motion_level_returns_float(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        import cv2
        det = MotionDetector(default_config)
        gray = cv2.cvtColor(blank_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        det.prev_frame = gray
        level = det._compute_motion_level(gray)
        assert isinstance(level, float)
        assert level == 0.0


# ---------------------------------------------------------------------------
# ColorDetector
# ---------------------------------------------------------------------------

class TestColorDetector:
    def test_no_alerts_while_building_baseline(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = ColorDetector(default_config)
        for _ in range(50):
            alerts = det.process(blank_frame)
        assert alerts == []

    def test_color_change_after_baseline(
        self, default_config: DetectorConfig
    ) -> None:
        det = ColorDetector(default_config)
        blue = np.full((480, 640, 3), [200, 100, 50], dtype=np.uint8)
        for _ in range(110):
            det.process(blue)

        green = np.full((480, 640, 3), [50, 200, 50], dtype=np.uint8)
        alerts = det.process(green)
        types = {a.type for a in alerts}
        assert AlertType.COLOR_CHANGE in types or AlertType.WATER_CLOUDY in types

    def test_extract_center_region_shape(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = ColorDetector(default_config)
        center = det._extract_center_region(blank_frame)
        h, w = blank_frame.shape[:2]
        assert center.shape[0] == h // 2
        assert center.shape[1] == w // 2


# ---------------------------------------------------------------------------
# ZoneDetector
# ---------------------------------------------------------------------------

class TestZoneDetector:
    def test_no_alerts_on_blank_frame(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = ZoneDetector(default_config)
        alerts = det.process(blank_frame)
        assert alerts == []

    def test_surface_bright_starts_tracking(
        self, default_config: DetectorConfig
    ) -> None:
        det = ZoneDetector(default_config)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Make top 15% very bright
        surface_h = int(480 * 0.15)
        frame[:surface_h, :] = 255
        det.process(frame)
        assert det.surface_activity_start is not None

    def test_get_zone_activity(self, default_config: DetectorConfig) -> None:
        det = ZoneDetector(default_config)
        zone = np.zeros((100, 100), dtype=np.uint8)
        assert det._get_zone_activity(zone) == 0.0
        zone[:] = 200
        assert det._get_zone_activity(zone) > 0


# ---------------------------------------------------------------------------
# FishCountDetector
# ---------------------------------------------------------------------------

class TestFishCountDetector:
    def test_blank_frame_zero_fish(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = FishCountDetector(default_config)
        alerts = det.process(blank_frame)
        assert det.count_history[-1] == 0
        assert alerts == []

    def test_count_fish_objects_returns_int(
        self, default_config: DetectorConfig, noisy_frame: np.ndarray
    ) -> None:
        det = FishCountDetector(default_config)
        count = det._count_fish_objects(noisy_frame)
        assert isinstance(count, int)
        assert count >= 0


# ---------------------------------------------------------------------------
# FilterDetector
# ---------------------------------------------------------------------------

class TestFilterDetector:
    def test_no_alerts_before_baseline(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = FilterDetector(default_config)
        for _ in range(50):
            alerts = det.process(blank_frame)
        assert alerts == []

    def test_measure_bubble_activity_returns_float(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = FilterDetector(default_config)
        val = det._measure_bubble_activity(blank_frame)
        assert isinstance(val, float)


# ---------------------------------------------------------------------------
# CoolMomentDetector
# ---------------------------------------------------------------------------

class TestCoolMomentDetector:
    def test_no_alerts_before_baseline(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        det = CoolMomentDetector(default_config)
        for _ in range(30):
            alerts = det.process(blank_frame)
        assert alerts == []

    def test_cooldown_prevents_rapid_alerts(
        self, default_config: DetectorConfig
    ) -> None:
        det = CoolMomentDetector(default_config)
        det.last_cool_moment = time.time()  # just fired
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        alerts = det.process(frame)
        assert alerts == []


# ---------------------------------------------------------------------------
# FishWatcherDetector (aggregator)
# ---------------------------------------------------------------------------

class TestFishWatcherDetector:
    def test_processes_all_detectors(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        fwd = FishWatcherDetector(default_config)
        assert len(fwd.detectors) == 6
        alerts = fwd.process(blank_frame)
        assert isinstance(alerts, list)

    def test_cooldown_filters_duplicates(
        self, default_config: DetectorConfig
    ) -> None:
        fwd = FishWatcherDetector(default_config)
        fwd.last_alert_time[AlertType.NO_MOTION] = time.time()
        assert not fwd._check_cooldown(AlertType.NO_MOTION)
        fwd.last_alert_time[AlertType.NO_MOTION] = time.time() - 120
        assert fwd._check_cooldown(AlertType.NO_MOTION)

    def test_process_handles_detector_error(
        self, default_config: DetectorConfig, blank_frame: np.ndarray
    ) -> None:
        """If a sub-detector raises, the aggregator continues."""
        fwd = FishWatcherDetector(default_config)

        class BrokenDetector(BaseDetector):
            def process(self, frame: np.ndarray) -> list[Alert]:
                raise RuntimeError("boom")

        fwd.detectors.insert(0, BrokenDetector(default_config))
        # Should not raise
        alerts = fwd.process(blank_frame)
        assert isinstance(alerts, list)


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

class TestAlert:
    def test_defaults(self) -> None:
        a = Alert(type=AlertType.NO_MOTION, message="test", confidence=0.5)
        assert a.frame is None
        assert a.is_cool_moment is False
        assert isinstance(a.timestamp, float)
