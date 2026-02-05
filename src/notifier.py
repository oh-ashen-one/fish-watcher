"""
Notification system for sending alerts to Clawdbot/user.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .detector import Alert, AlertType
from .vision import ClaudeVisionAnalyzer, analyze_for_clawdbot


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    message: str
    response: Optional[str] = None


class ClawdbotNotifier:
    """Sends notifications through Clawdbot."""
    
    # Alert type to emoji mapping
    EMOJI_MAP = {
        # Health/Emergency
        AlertType.NO_MOTION: "⚠️",
        AlertType.MOTION_SPIKE: "🚨",
        AlertType.FISH_FLOATING: "☠️",
        AlertType.FISH_BOTTOM: "⬇️",
        AlertType.ERRATIC_SWIMMING: "🌀",
        AlertType.GASPING_SURFACE: "😮",
        AlertType.AGGRESSION: "⚔️",
        
        # Tank Issues
        AlertType.COLOR_CHANGE: "💧",
        AlertType.WATER_CLOUDY: "🌫️",
        AlertType.ALGAE_GROWTH: "🌿",
        AlertType.WATER_LEVEL_DROP: "📉",
        AlertType.FILTER_STOPPED: "🔌",
        AlertType.LIGHT_STUCK: "💡",
        
        # Behavior
        AlertType.SURFACE_ACTIVITY: "🐟",
        AlertType.HIDING_TOO_LONG: "🙈",
        AlertType.MISSED_FEEDING: "🍽️",
        AlertType.CLUSTERING: "👥",
        AlertType.LOW_ACTIVITY: "😴",
        
        # Cool Moments
        AlertType.INTERESTING_MOMENT: "✨",
        AlertType.FEEDING_FRENZY: "🎉",
        AlertType.FISH_PLAYING: "🎮",
        AlertType.NEW_BEHAVIOR: "🆕",
    }
    
    # Priority levels
    PRIORITY_MAP = {
        AlertType.NO_MOTION: "high",
        AlertType.MOTION_SPIKE: "medium",
        AlertType.FISH_FLOATING: "critical",
        AlertType.FISH_BOTTOM: "high",
        AlertType.ERRATIC_SWIMMING: "high",
        AlertType.GASPING_SURFACE: "critical",
        AlertType.COLOR_CHANGE: "medium",
        AlertType.WATER_CLOUDY: "medium",
        AlertType.FILTER_STOPPED: "high",
        AlertType.SURFACE_ACTIVITY: "medium",
        AlertType.LOW_ACTIVITY: "medium",
        AlertType.INTERESTING_MOMENT: "low",
        AlertType.FEEDING_FRENZY: "low",
    }
    
    def __init__(self, workspace_dir: str = None, enable_vision: bool = True):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.home() / "clawd"
        self.alert_log = self.workspace_dir / "fish-watcher-alerts.json"
        self.enable_vision = enable_vision
        self.vision_analyzer = ClaudeVisionAnalyzer() if enable_vision else None
        
    def notify(self, alert: Alert, clip_path: Optional[str] = None) -> NotificationResult:
        """Send an alert notification."""
        emoji = self.EMOJI_MAP.get(alert.type, "🔔")
        priority = self.PRIORITY_MAP.get(alert.type, "medium")
        
        # Build the message
        message_parts = [
            f"{emoji} **Fish Tank Alert**",
            f"",
            f"**Type:** {alert.type.value.replace('_', ' ').title()}",
            f"**Message:** {alert.message}",
            f"**Confidence:** {alert.confidence:.0%}",
        ]
        
        if clip_path and Path(clip_path).exists():
            message_parts.append(f"")
            message_parts.append(f"📹 Clip saved: `{clip_path}`")
        
        message = "\n".join(message_parts)
        
        # Run vision analysis if enabled
        vision_analysis = None
        if self.enable_vision and clip_path and Path(clip_path).exists():
            print(f"[Notifier] Running Claude vision analysis on {clip_path}...")
            try:
                vision_analysis = analyze_for_clawdbot(clip_path)
                if vision_analysis and "error" not in vision_analysis:
                    print(f"[Notifier] Vision analysis: {vision_analysis.get('summary', 'N/A')}")
            except Exception as e:
                print(f"[Notifier] Vision analysis failed: {e}")
        
        # Log the alert
        self._log_alert(alert, clip_path)
        
        # Write to a file that Clawdbot can pick up
        alert_file = self.workspace_dir / "fish-watcher-pending-alert.json"
        alert_data = {
            "type": alert.type.value,
            "message": message,
            "clip_path": clip_path,
            "priority": priority,
            "timestamp": alert.timestamp,
            "confidence": alert.confidence,
            "vision_analysis": vision_analysis,
        }
        
        try:
            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2)
            
            print(f"[Notifier] Alert written to {alert_file}")
            return NotificationResult(success=True, message="Alert queued for Clawdbot")
            
        except Exception as e:
            return NotificationResult(success=False, message=f"Failed to write alert: {e}")
    
    def _log_alert(self, alert: Alert, clip_path: Optional[str]) -> None:
        """Log alert to history file."""
        history = []
        if self.alert_log.exists():
            try:
                with open(self.alert_log) as f:
                    history = json.load(f)
            except:
                pass
        
        history.append({
            "type": alert.type.value,
            "message": alert.message,
            "confidence": alert.confidence,
            "timestamp": alert.timestamp,
            "clip_path": clip_path,
        })
        
        # Keep last 100 alerts
        history = history[-100:]
        
        with open(self.alert_log, 'w') as f:
            json.dump(history, f, indent=2)


class WebhookNotifier:
    """Sends notifications via webhook."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    def notify(self, alert: Alert, clip_path: Optional[str] = None) -> NotificationResult:
        """Send alert via webhook."""
        import urllib.request
        import urllib.error
        
        payload = {
            "type": alert.type.value,
            "message": alert.message,
            "confidence": alert.confidence,
            "timestamp": alert.timestamp,
            "clip_path": clip_path,
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return NotificationResult(
                    success=True,
                    message="Webhook sent",
                    response=response.read().decode()
                )
                
        except urllib.error.URLError as e:
            return NotificationResult(success=False, message=f"Webhook failed: {e}")
