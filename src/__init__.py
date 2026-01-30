"""
Fish Watcher - AI-powered fish tank monitoring.
"""

from .watcher import FishWatcher
from .detector import FishWatcherDetector, Alert, AlertType
from .buffer import RollingBuffer
from .recorder import ClipRecorder
from .notifier import ClawdbotNotifier

__version__ = "0.1.0"
__all__ = [
    "FishWatcher",
    "FishWatcherDetector", 
    "Alert",
    "AlertType",
    "RollingBuffer",
    "ClipRecorder",
    "ClawdbotNotifier",
]
