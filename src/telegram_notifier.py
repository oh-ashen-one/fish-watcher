"""
Telegram notifications for fish tank alerts.
Uses Bot API - just need a bot token and chat ID.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from datetime import datetime

from .detector import Alert, AlertType


class TelegramNotifier:
    """Send alerts directly to Telegram via Bot API."""
    
    ALERT_EMOJI = {
        AlertType.NO_MOTION: "⚠️",
        AlertType.MOTION_SPIKE: "🚨",
        AlertType.FISH_FLOATING: "☠️",
        AlertType.FISH_BOTTOM: "⬇️",
        AlertType.ERRATIC_SWIMMING: "🌀",
        AlertType.GASPING_SURFACE: "😮",
        AlertType.WATER_CLOUDY: "🌫️",
        AlertType.ALGAE_GROWTH: "🌿",
        AlertType.FILTER_STOPPED: "🔌",
        AlertType.CLUSTERING: "👥",
        AlertType.LOW_ACTIVITY: "😴",
        AlertType.FEEDING_FRENZY: "🎉",
        AlertType.INTERESTING_MOMENT: "✨",
    }
    
    def __init__(self, bot_token: str, chat_id: str, tank_name: str = "Fish Tank"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.tank_name = tank_name
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    def notify(self, alert: Alert, clip_path: Optional[str] = None,
               vision_analysis: Optional[dict] = None,
               fish_name: Optional[str] = None) -> bool:
        """Send alert to Telegram."""
        emoji = self.ALERT_EMOJI.get(alert.type, "🔔")
        
        # Build message
        lines = [
            f"{emoji} *{self.tank_name} Alert*",
            "",
            f"*Type:* {alert.type.value.replace('_', ' ').title()}",
            f"*Confidence:* {alert.confidence:.0%}",
        ]
        
        if fish_name:
            lines.insert(2, f"*Fish:* {fish_name}")
        
        if alert.message:
            lines.append(f"\n_{alert.message}_")
        
        if vision_analysis and vision_analysis.get("summary"):
            lines.append(f"\n🧠 *AI Analysis:*\n{vision_analysis['summary']}")
        
        if clip_path:
            lines.append(f"\n📹 Clip: `{Path(clip_path).name}`")
        
        text = "\n".join(lines)
        
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/sendMessage",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                return result.get("ok", False)
                
        except Exception as e:
            print(f"[Telegram] Failed to send: {e}")
            return False
    
    def send_video(self, video_path: str, caption: str = "") -> bool:
        """Send a video clip to Telegram."""
        try:
            import subprocess
            # Use curl for multipart upload (simpler than urllib)
            cmd = [
                "curl", "-s", "-X", "POST",
                f"{self.base_url}/sendVideo",
                "-F", f"chat_id={self.chat_id}",
                "-F", f"video=@{video_path}",
                "-F", f"caption={caption}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return "ok" in result.stdout.lower()
        except Exception as e:
            print(f"[Telegram] Failed to send video: {e}")
            return False
    
    def send_daily_report(self, report: dict) -> bool:
        """Send daily health report."""
        health = report.get("health_score", "?")
        alerts = report.get("alert_count", 0)
        clips = report.get("clip_count", 0)
        
        if isinstance(health, (int, float)):
            if health >= 90:
                emoji = "🌟"
            elif health >= 70:
                emoji = "✅"
            elif health >= 50:
                emoji = "⚠️"
            else:
                emoji = "🚨"
        else:
            emoji = "📊"
        
        text = f"""📊 *Daily Fish Report*

{emoji} *Health Score:* {health}/100
🚨 *Alerts:* {alerts}
📹 *Clips:* {clips}

_Fish Watcher AI_"""
        
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/sendMessage",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                return result.get("ok", False)
                
        except Exception as e:
            print(f"[Telegram] Failed to send report: {e}")
            return False
