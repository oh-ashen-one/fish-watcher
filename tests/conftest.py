"""Shared fixtures for fish-watcher tests."""

import numpy as np
import pytest

from src.detector import DetectorConfig


@pytest.fixture
def default_config() -> DetectorConfig:
    """Default detector config for testing."""
    return DetectorConfig()


@pytest.fixture
def blank_frame() -> np.ndarray:
    """A solid black 640x480 BGR frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def white_frame() -> np.ndarray:
    """A solid white 640x480 BGR frame."""
    return np.full((480, 640, 3), 255, dtype=np.uint8)


@pytest.fixture
def noisy_frame() -> np.ndarray:
    """A random-noise 640x480 BGR frame (deterministic seed)."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def gradient_frame() -> np.ndarray:
    """A vertical gradient frame (black at top, white at bottom)."""
    grad = np.linspace(0, 255, 480, dtype=np.uint8)
    frame = np.tile(grad[:, None, None], (1, 640, 3))
    return frame.astype(np.uint8)
