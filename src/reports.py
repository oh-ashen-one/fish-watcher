"""
Daily and weekly reports for fish tank status.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class DailyStats:
    """Statistics for a single day."""
    date: str
    total_alerts: int
    alerts_by_type: dict
    avg_activity_level: float
    peak_activity_time: str
    lowest_activity_time: str
    clips_recorded: int
    cool_moments: int
    health_score: int  # 0-100


class ReportGenerator:
    """Generates daily and weekly reports."""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.data_dir / "stats.json"
        
        # Daily tracking
        self.today_alerts: list = []
        self.activity_samples: list = []
        self.clips_today: int = 0
        self.cool_moments_today: int = 0
        self.current_date: str = datetime.now().strftime("%Y-%m-%d")
        
    def record_alert(self, alert_type: str, is_cool: bool = False) -> None:
        """Record an alert for daily stats."""
        self._check_day_rollover()
        
        self.today_alerts.append({
            "type": alert_type,
            "time": datetime.now().strftime("%H:%M:%S"),
            "is_cool": is_cool
        })
        
        if is_cool:
            self.cool_moments_today += 1
    
    def record_activity(self, level: float) -> None:
        """Record an activity sample."""
        self._check_day_rollover()
        
        self.activity_samples.append({
            "level": level,
            "time": datetime.now().strftime("%H:%M:%S")
        })
    
    def record_clip(self) -> None:
        """Record that a clip was saved."""
        self._check_day_rollover()
        self.clips_today += 1
    
    def _check_day_rollover(self) -> None:
        """Check if we've rolled over to a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.current_date:
            self._save_daily_stats()
            self._reset_daily()
            self.current_date = today
    
    def _reset_daily(self) -> None:
        """Reset daily counters."""
        self.today_alerts = []
        self.activity_samples = []
        self.clips_today = 0
        self.cool_moments_today = 0
    
    def _save_daily_stats(self) -> None:
        """Save daily stats to file."""
        if not self.activity_samples:
            return
        
        # Calculate stats
        activity_levels = [s["level"] for s in self.activity_samples]
        activity_times = [s["time"] for s in self.activity_samples]
        
        peak_idx = np.argmax(activity_levels)
        low_idx = np.argmin(activity_levels)
        
        # Count alerts by type
        alerts_by_type = {}
        for alert in self.today_alerts:
            t = alert["type"]
            alerts_by_type[t] = alerts_by_type.get(t, 0) + 1
        
        # Calculate health score
        health_score = self._calculate_health_score(alerts_by_type)
        
        stats = DailyStats(
            date=self.current_date,
            total_alerts=len(self.today_alerts),
            alerts_by_type=alerts_by_type,
            avg_activity_level=float(np.mean(activity_levels)),
            peak_activity_time=activity_times[peak_idx] if activity_times else "N/A",
            lowest_activity_time=activity_times[low_idx] if activity_times else "N/A",
            clips_recorded=self.clips_today,
            cool_moments=self.cool_moments_today,
            health_score=health_score
        )
        
        # Load existing stats
        all_stats = self._load_stats()
        all_stats[self.current_date] = stats.__dict__
        
        # Keep last 30 days
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        all_stats = {k: v for k, v in all_stats.items() if k >= cutoff}
        
        with open(self.stats_file, 'w') as f:
            json.dump(all_stats, f, indent=2)
    
    def _load_stats(self) -> dict:
        """Load existing stats."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _calculate_health_score(self, alerts_by_type: dict) -> int:
        """Calculate overall health score 0-100."""
        score = 100
        
        # Deduct points for concerning alerts
        deductions = {
            "no_motion": 20,
            "fish_floating": 30,
            "fish_stuck_bottom": 25,
            "erratic_swimming": 15,
            "gasping_surface": 25,
            "water_cloudy": 10,
            "filter_stopped": 20,
            "low_activity": 15,
        }
        
        for alert_type, count in alerts_by_type.items():
            if alert_type in deductions:
                score -= deductions[alert_type] * min(count, 3)  # Cap at 3x
        
        return max(0, score)
    
    def generate_daily_report(self) -> str:
        """Generate a text report for today."""
        self._check_day_rollover()
        
        if not self.activity_samples:
            return "📊 **Daily Fish Report**\n\nNot enough data yet. Check back later!"
        
        activity_levels = [s["level"] for s in self.activity_samples]
        avg_activity = np.mean(activity_levels)
        
        # Count alerts
        alert_counts = {}
        for alert in self.today_alerts:
            t = alert["type"]
            alert_counts[t] = alert_counts.get(t, 0) + 1
        
        health_score = self._calculate_health_score(alert_counts)
        
        # Build report
        lines = [
            f"📊 **Daily Fish Report** - {self.current_date}",
            "",
            f"🏥 **Health Score:** {health_score}/100",
            "",
            "📈 **Activity:**",
            f"  • Average: {avg_activity:.1f}",
            f"  • Samples: {len(self.activity_samples)}",
            "",
            f"🚨 **Alerts:** {len(self.today_alerts)}",
        ]
        
        if alert_counts:
            for alert_type, count in sorted(alert_counts.items()):
                emoji = "⚠️" if count > 2 else "📝"
                lines.append(f"  {emoji} {alert_type}: {count}")
        else:
            lines.append("  ✅ No alerts!")
        
        lines.extend([
            "",
            f"📹 **Clips:** {self.clips_today}",
            f"✨ **Cool moments:** {self.cool_moments_today}",
        ])
        
        # Health commentary
        lines.append("")
        if health_score >= 90:
            lines.append("🐟 Your fish are thriving!")
        elif health_score >= 70:
            lines.append("🐟 Fish are doing okay, minor concerns.")
        elif health_score >= 50:
            lines.append("⚠️ Some issues detected - check on your tank.")
        else:
            lines.append("🚨 Multiple issues - tank needs attention!")
        
        return "\n".join(lines)
    
    def generate_weekly_report(self) -> str:
        """Generate a weekly summary report."""
        all_stats = self._load_stats()
        
        if len(all_stats) < 2:
            return "📊 **Weekly Report**\n\nNeed more data for weekly report."
        
        # Get last 7 days
        dates = sorted(all_stats.keys())[-7:]
        
        total_alerts = sum(all_stats[d]["total_alerts"] for d in dates)
        total_clips = sum(all_stats[d]["clips_recorded"] for d in dates)
        total_cool = sum(all_stats[d]["cool_moments"] for d in dates)
        avg_health = np.mean([all_stats[d]["health_score"] for d in dates])
        
        # Find trends
        health_scores = [all_stats[d]["health_score"] for d in dates]
        trend = "📈 improving" if health_scores[-1] > health_scores[0] else "📉 declining" if health_scores[-1] < health_scores[0] else "➡️ stable"
        
        lines = [
            "📊 **Weekly Fish Report**",
            f"📅 {dates[0]} to {dates[-1]}",
            "",
            f"🏥 **Avg Health Score:** {avg_health:.0f}/100 ({trend})",
            "",
            "📈 **This Week:**",
            f"  • Total alerts: {total_alerts}",
            f"  • Clips recorded: {total_clips}",
            f"  • Cool moments: {total_cool}",
            "",
            "📅 **Daily Health Scores:**",
        ]
        
        for d in dates:
            score = all_stats[d]["health_score"]
            bar = "█" * (score // 10) + "░" * (10 - score // 10)
            lines.append(f"  {d[-5:]}: {bar} {score}")
        
        return "\n".join(lines)
