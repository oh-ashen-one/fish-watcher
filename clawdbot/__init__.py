"""
Fish Watcher - Clawdbot Integration
"""

from .controller import (
    status,
    start,
    stop,
    list_cameras,
    capture_frame,
    set_config,
    get_report,
    get_pending_alert,
    list_clips,
)

__all__ = [
    "status",
    "start", 
    "stop",
    "list_cameras",
    "capture_frame",
    "set_config",
    "get_report",
    "get_pending_alert",
    "list_clips",
]
