"""
Fish Watcher - AI-powered fish tank monitoring.
"""

from .watcher import FishWatcher
from .detector import FishWatcherDetector, Alert, AlertType
from .buffer import RollingBuffer
from .recorder import ClipRecorder
from .notifier import ClawdbotNotifier
from .reports import ReportGenerator
from .vision import ClaudeVisionAnalyzer, analyze_for_clawdbot
from .multi_tank import MultiTankWatcher, TankWatcher, TankConfig
from .fish_counter import FishCounter, FishBlob, count_fish_in_image

__version__ = "1.2.0"
__all__ = [
    "FishWatcher",
    "FishWatcherDetector", 
    "Alert",
    "AlertType",
    "RollingBuffer",
    "ClipRecorder",
    "ClawdbotNotifier",
    "ReportGenerator",
    "ClaudeVisionAnalyzer",
    "analyze_for_clawdbot",
    "MultiTankWatcher",
    "TankWatcher",
    "TankConfig",
    "FishCounter",
    "FishBlob",
    "count_fish_in_image",
]
