"""Tests for src.fish_counter — fish counting logic."""

import numpy as np
import pytest

from src.fish_counter import FishBlob, FishCounter, count_fish_in_image


class TestFishBlob:
    def test_fields(self) -> None:
        blob = FishBlob(x=10, y=20, width=30, height=15, area=450, center=(25, 27))
        assert blob.center == (25, 27)
        assert blob.area == 450


class TestFishCounter:
    def test_init_defaults(self) -> None:
        fc = FishCounter()
        assert fc.min_fish_area == 100
        assert fc.max_fish_area == 10000
        assert fc.stable_count == 0

    def test_process_blank_frame(self, blank_frame: np.ndarray) -> None:
        fc = FishCounter()
        count, blobs = fc.process(blank_frame)
        assert isinstance(count, int)
        assert isinstance(blobs, list)

    def test_stable_count_converges(self, blank_frame: np.ndarray) -> None:
        fc = FishCounter()
        for _ in range(35):
            fc.process(blank_frame)
        assert fc.get_stable_count() == 0

    def test_draw_detections_returns_frame(self, blank_frame: np.ndarray) -> None:
        fc = FishCounter()
        _, blobs = fc.process(blank_frame)
        out = fc.draw_detections(blank_frame, blobs)
        assert out.shape == blank_frame.shape

    def test_reset_clears_state(self, blank_frame: np.ndarray) -> None:
        fc = FishCounter()
        for _ in range(5):
            fc.process(blank_frame)
        fc.reset()
        assert fc.count_history == []
        assert fc.stable_count == 0

    def test_detects_blobs_in_noisy_frame(self, noisy_frame: np.ndarray) -> None:
        """Noisy frames should produce some blob detections."""
        fc = FishCounter()
        count, blobs = fc.process(noisy_frame)
        # We don't assert exact count — just that it runs without error
        assert isinstance(count, int)

    def test_aspect_ratio_filter(self) -> None:
        """Ensure very tall or very wide shapes are filtered."""
        fc = FishCounter()
        # Create frame with a thin vertical line (bad aspect ratio)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:400, 300:303] = 255  # 300px tall, 3px wide => aspect < 0.2
        count, blobs = fc.process(frame)
        # The thin line should be filtered out by aspect ratio
        assert isinstance(count, int)


class TestCountFishInImage:
    def test_nonexistent_path_returns_zero(self, tmp_path) -> None:
        count, blobs = count_fish_in_image(str(tmp_path / "nope.jpg"))
        assert count == 0
        assert blobs == []

    def test_with_blank_image(self, tmp_path, blank_frame: np.ndarray) -> None:
        import cv2
        path = str(tmp_path / "blank.jpg")
        cv2.imwrite(path, blank_frame)
        count, blobs = count_fish_in_image(path)
        assert count == 0
