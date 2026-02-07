"""
Discord webhook notifications for fish tank alerts.
No bot token needed - just a webhook URL.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from datetime import datetime

from .detector import Alert, AlertType


class DiscordNotifier:
    """Send alerts directly to Discord via webhook."""
    
    # Fun alert messages by type
    ALERT_MESSAGES = {
        # Health/Emergency - concerned but helpful
        AlertType.NO_MOTION: [
            "👀 Haven't seen any movement in a while...",
            "🤔 Your fish are being suspiciously still",
            "😴 Either naptime or we should check on them",
        ],
        AlertType.FISH_FLOATING: [
            "🚨 This doesn't look good - fish floating at surface",
            "⚠️ Urgent: Possible floater detected",
        ],
        AlertType.FISH_BOTTOM: [
            "⬇️ Someone's been chilling at the bottom too long",
            "🐟 Fish stuck at substrate - might be stressed",
        ],
        AlertType.ERRATIC_SWIMMING: [
            "🌀 Whoa! Someone's doing zoomies... or panicking",
            "💨 Wild swimming detected - stress or just vibes?",
        ],
        AlertType.GASPING_SURFACE: [
            "😮 Fish gasping at surface - check oxygen/filter!",
            "🫁 Surface breathing detected - possible O2 issue",
        ],
        
        # Tank Issues - informative
        AlertType.WATER_CLOUDY: [
            "🌫️ Water looking a bit murky today",
            "💧 Cloudiness detected - might need a water change",
        ],
        AlertType.ALGAE_GROWTH: [
            "🌿 Getting a bit green in there...",
            "🪴 Algae bloom starting - time for some scrubbing?",
        ],
        AlertType.FILTER_STOPPED: [
            "🔌 Filter might have stopped - no bubble activity",
            "⚠️ Equipment check needed - filter seems off",
        ],
        AlertType.COLOR_CHANGE: [
            "🎨 Water color shifted - keeping an eye on it",
        ],
        
        # Behavior - curious
        AlertType.CLUSTERING: [
            "👥 Everyone's huddled in the corner - group meeting?",
            "🐟🐟🐟 Fish clustering detected - stress or social hour?",
        ],
        AlertType.LOW_ACTIVITY: [
            "😴 Activity levels are down - lazy day or concerning?",
            "📉 Less movement than usual today",
        ],
        
        # Cool Moments - excited!
        AlertType.FEEDING_FRENZY: [
            "🎉 FEEDING FRENZY! They're going wild!",
            "🍽️ Dinner time chaos - caught on camera!",
            "😋 NOM NOM NOM - feeding time highlights!",
        ],
        AlertType.INTERESTING_MOMENT: [
            "✨ Caught something cool happening!",
            "📸 Interesting moment captured!",
            "🎬 Your fish did something worth watching",
        ],
        AlertType.FISH_PLAYING: [
            "🎮 Playtime detected! Fish having fun",
            "🐟💨 Chase sequence captured!",
        ],
    }
    
    # Emoji for embed color
    SEVERITY_COLORS = {
        "critical": 0xFF0000,  # Red
        "high": 0xFF6B35,      # Orange
        "medium": 0xFFD700,    # Yellow
        "low": 0x00FF88,       # Green (cool moments)
        "info": 0x00D4FF,      # Cyan
    }
    
    def __init__(self, webhook_url: str, tank_name: str = "Fish Tank"):
        self.webhook_url = webhook_url
        self.tank_name = tank_name
        
    def _get_severity(self, alert_type: AlertType) -> str:
        critical = {AlertType.FISH_FLOATING, AlertType.GASPING_SURFACE}
        high = {AlertType.NO_MOTION, AlertType.FISH_BOTTOM, AlertType.ERRATIC_SWIMMING, AlertType.FILTER_STOPPED}
        low = {AlertType.FEEDING_FRENZY, AlertType.INTERESTING_MOMENT, AlertType.FISH_PLAYING}
        
        if alert_type in critical:
            return "critical"
        elif alert_type in high:
            return "high"
        elif alert_type in low:
            return "low"
        return "medium"
    
    def _get_message(self, alert_type: AlertType) -> str:
        import random
        messages = self.ALERT_MESSAGES.get(alert_type, ["🔔 Alert from your fish tank"])
        return random.choice(messages)
    
    def notify(self, alert: Alert, clip_path: Optional[str] = None, 
               vision_analysis: Optional[dict] = None,
               fish_name: Optional[str] = None) -> bool:
        """Send alert to Discord."""
        severity = self._get_severity(alert.type)
        color = self.SEVERITY_COLORS.get(severity, 0x00D4FF)
        
        # Build embed
        embed = {
            "title": f"🐟 {self.tank_name}",
            "description": self._get_message(alert.type),
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "Type",
                    "value": alert.type.value.replace("_", " ").title(),
                    "inline": True,
                },
                {
                    "name": "Confidence",
                    "value": f"{alert.confidence:.0%}",
                    "inline": True,
                },
            ],
            "footer": {
                "text": "Fish Watcher AI",
            }
        }
        
        # Add fish name if known
        if fish_name:
            embed["fields"].insert(0, {
                "name": "Who",
                "value": f"🐟 {fish_name}",
                "inline": True,
            })
        
        # Add vision analysis if available
        if vision_analysis and vision_analysis.get("summary"):
            embed["fields"].append({
                "name": "🧠 AI Analysis",
                "value": vision_analysis["summary"][:1024],
                "inline": False,
            })
            
            if vision_analysis.get("recommendations"):
                recs = vision_analysis["recommendations"]
                if isinstance(recs, list):
                    recs = "\n".join(f"• {r}" for r in recs[:3])
                embed["fields"].append({
                    "name": "💡 Recommendations",
                    "value": recs[:1024],
                    "inline": False,
                })
        
        # Add clip info
        if clip_path:
            embed["fields"].append({
                "name": "📹 Clip",
                "value": f"`{Path(clip_path).name}`",
                "inline": False,
            })
        
        # Cool moment? Add celebration
        if alert.is_cool_moment:
            embed["title"] = f"✨ {self.tank_name} - Cool Moment!"
        
        payload = {
            "embeds": [embed],
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 204 or response.status == 200
                
        except Exception as e:
            print(f"[Discord] Failed to send: {e}")
            return False
    
    def send_daily_report(self, report: dict) -> bool:
        """Send daily health report to Discord."""
        health = report.get("health_score", "?")
        alerts = report.get("alert_count", 0)
        clips = report.get("clip_count", 0)
        peak = report.get("peak_activity_time", "Unknown")
        
        # Health emoji
        if isinstance(health, (int, float)):
            if health >= 90:
                health_emoji = "🌟"
                health_msg = "Your fish are thriving!"
            elif health >= 70:
                health_emoji = "✅"
                health_msg = "Looking good overall"
            elif health >= 50:
                health_emoji = "⚠️"
                health_msg = "Some concerns to watch"
            else:
                health_emoji = "🚨"
                health_msg = "Needs attention"
        else:
            health_emoji = "📊"
            health_msg = "Not enough data yet"
        
        embed = {
            "title": f"📊 Daily Fish Report",
            "description": f"{health_emoji} {health_msg}",
            "color": 0x00D4FF,
            "fields": [
                {"name": "🏥 Health Score", "value": f"{health}/100", "inline": True},
                {"name": "🚨 Alerts", "value": str(alerts), "inline": True},
                {"name": "📹 Clips", "value": str(clips), "inline": True},
                {"name": "📈 Peak Activity", "value": peak, "inline": True},
            ],
            "footer": {"text": "Fish Watcher AI • Daily Report"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        payload = {"embeds": [embed]}
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status in (200, 204)
                
        except Exception as e:
            print(f"[Discord] Failed to send report: {e}")
            return False
