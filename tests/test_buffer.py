"""Tests for src.buffer — rolling frame buffer."""

import time
import numpy as np
import pytest

from src.buffer import BufferedFrame, RollingBuffer


class TestRollingBuffer:
    def test_add_and_len(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=5, fps=10)
        assert len(buf) == 0
        buf.add(blank_frame)
        assert len(buf) == 1

    def test_max_capacity(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=1, fps=5)  # max 5 frames
        for _ in range(10):
            buf.add(blank_frame)
        assert len(buf) == 5

    def test_get_all_returns_list(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=5, fps=10)
        buf.add(blank_frame)
        frames = buf.get_all()
        assert len(frames) == 1
        assert isinstance(frames[0], BufferedFrame)

    def test_get_recent(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=10, fps=10)
        buf.add(blank_frame)
        time.sleep(0.05)
        recent = buf.get_recent(1.0)
        assert len(recent) == 1

    def test_clear(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=5, fps=10)
        buf.add(blank_frame)
        buf.clear()
        assert len(buf) == 0

    def test_duration_empty(self) -> None:
        buf = RollingBuffer()
        assert buf.duration == 0

    def test_frames_are_copies(self, blank_frame: np.ndarray) -> None:
        buf = RollingBuffer(max_seconds=5, fps=10)
        buf.add(blank_frame)
        blank_frame[:] = 128  # Mutate original
        stored = buf.get_all()[0].frame
        assert stored[0, 0, 0] == 0  # Should still be black
