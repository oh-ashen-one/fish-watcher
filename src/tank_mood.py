#!/usr/bin/env python3
"""
Tank Mood - Fun personality indicator for your aquarium.
Analyzes recent activity and gives your tank a "vibe".
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict


@dataclass
class TankMood:
    """The current mood/vibe of the tank."""
    mood: str           # e.g., "zen", "playful", "hangry"
    emoji: str          # e.g., "😌", "🎉", "😤"
    description: str    # Human-readable explanation
    confidence: float   # 0-1
    activity_level: str # "sleepy", "chill", "active", "hyperactive"
    health_vibe: str    # "thriving", "good", "meh", "concerning"
    

class TankMoodAnalyzer:
    """Analyze tank activity and determine the 'mood'."""
    
    MOODS = {
        # (activity_level, health_status, time_of_day) -> mood
        ("sleepy", "good", "night"): ("😴", "zen", "Everyone's resting peacefully"),
        ("sleepy", "good", "day"): ("😌", "peaceful", "Calm and collected today"),
        ("chill", "good", "any"): ("🐟", "vibin", "Just swimming around, living life"),
        ("active", "good", "any"): ("🎉", "playful", "Lots of activity! Happy fish"),
        ("hyperactive", "good", "any"): ("🤪", "zoomies", "MAXIMUM ENERGY"),
        ("active", "meh", "any"): ("🤔", "restless", "Something's got them stirred up"),
        ("hyperactive", "meh", "any"): ("😰", "stressed", "Unusually frantic - keep an eye out"),
        ("sleepy", "meh", "any"): ("😕", "lethargic", "Less active than usual - maybe check on them"),
        ("any", "concerning", "any"): ("🚨", "needs attention", "Some concerning signs today"),
        
        # Special moods
        ("feeding", "good", "any"): ("🍽️", "hangry", "FOOD FOOD FOOD"),
        ("hiding", "any", "any"): ("🙈", "shy", "Everyone's hiding today"),
        ("clustering", "any", "any"): ("🫂", "social", "Group hangout in progress"),
    }
    
    def __init__(self, data_dir: str = "./data", clips_dir: str = "./clips"):
        self.data_dir = Path(data_dir)
        self.clips_dir = Path(clips_dir)
        
    def get_recent_alerts(self, hours: int = 24) -> list[dict]:
        """Get alerts from the last N hours."""
        alerts = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # Check alert log
        alert_log = self.data_dir.parent / "fish-watcher-alerts.json"
        if alert_log.exists():
            try:
                with open(alert_log) as f:
                    all_alerts = json.load(f)
                    for alert in all_alerts:
                        ts = datetime.fromtimestamp(alert.get("timestamp", 0))
                        if ts > cutoff:
                            alerts.append(alert)
            except:
                pass
        
        return alerts
    
    def get_clip_stats(self, hours: int = 24) -> dict:
        """Analyze recent clips."""
        stats = defaultdict(int)
        cutoff = datetime.now() - timedelta(hours=hours)
        
        for f in self.clips_dir.glob("*.mp4"):
            try:
                parts = f.stem.split("_", 2)
                if len(parts) < 3:
                    continue
                dt = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                if dt > cutoff:
                    alert_type = parts[2]
                    stats[alert_type] += 1
                    stats["total"] += 1
            except:
                continue
        
        return dict(stats)
    
    def analyze_mood(self) -> TankMood:
        """Determine the current tank mood."""
        alerts = self.get_recent_alerts(hours=12)
        clips = self.get_clip_stats(hours=12)
        hour = datetime.now().hour
        
        # Determine time of day
        if 22 <= hour or hour < 6:
            time_of_day = "night"
        else:
            time_of_day = "day"
        
        # Count alert types
        alert_types = defaultdict(int)
        for alert in alerts:
            alert_types[alert.get("type", "unknown")] += 1
        
        # Determine activity level
        total_clips = clips.get("total", 0)
        if total_clips == 0:
            activity_level = "sleepy"
        elif total_clips <= 2:
            activity_level = "chill"
        elif total_clips <= 5:
            activity_level = "active"
        else:
            activity_level = "hyperactive"
        
        # Determine health status
        concerning_alerts = sum([
            alert_types.get("no_motion", 0),
            alert_types.get("fish_floating", 0),
            alert_types.get("gasping_surface", 0),
            alert_types.get("fish_stuck_bottom", 0),
        ])
        
        warning_alerts = sum([
            alert_types.get("water_cloudy", 0),
            alert_types.get("filter_stopped", 0),
            alert_types.get("erratic_swimming", 0),
        ])
        
        if concerning_alerts > 0:
            health_status = "concerning"
        elif warning_alerts > 0:
            health_status = "meh"
        else:
            health_status = "good"
        
        # Check for special conditions
        if clips.get("feeding_frenzy", 0) > 0:
            activity_level = "feeding"
        elif alert_types.get("hiding_too_long", 0) > 0:
            activity_level = "hiding"
        elif alert_types.get("fish_clustering", 0) > 0:
            activity_level = "clustering"
        
        # Find matching mood
        mood_key = None
        for key in self.MOODS:
            act, health, time = key
            if (act == activity_level or act == "any") and \
               (health == health_status or health == "any") and \
               (time == time_of_day or time == "any"):
                mood_key = key
                break
        
        if mood_key is None:
            mood_key = ("chill", "good", "any")  # Default
        
        emoji, mood_name, description = self.MOODS[mood_key]
        
        # Determine health vibe string
        health_vibes = {
            "good": "thriving",
            "meh": "okay",
            "concerning": "needs attention",
        }
        
        return TankMood(
            mood=mood_name,
            emoji=emoji,
            description=description,
            confidence=0.7 if len(alerts) > 3 else 0.5,
            activity_level=activity_level if activity_level not in ("feeding", "hiding", "clustering") else "active",
            health_vibe=health_vibes.get(health_status, "unknown"),
        )
    
    def get_activity_heatmap(self, days: int = 7) -> dict:
        """Generate hourly activity heatmap for the week."""
        heatmap = defaultdict(lambda: defaultdict(int))
        cutoff = datetime.now() - timedelta(days=days)
        
        for f in self.clips_dir.glob("*.mp4"):
            try:
                parts = f.stem.split("_", 2)
                if len(parts) < 2:
                    continue
                dt = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                if dt > cutoff:
                    day = dt.strftime("%a")  # Mon, Tue, etc.
                    hour = dt.hour
                    heatmap[day][hour] += 1
            except:
                continue
        
        return {day: dict(hours) for day, hours in heatmap.items()}
    
    def get_fish_favorites(self, days: int = 7) -> dict:
        """Determine favorite times, spots, etc."""
        clips = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for f in self.clips_dir.glob("*.mp4"):
            try:
                parts = f.stem.split("_", 2)
                if len(parts) < 3:
                    continue
                dt = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                if dt > cutoff:
                    clips.append({
                        "time": dt,
                        "hour": dt.hour,
                        "day": dt.strftime("%A"),
                        "type": parts[2],
                    })
            except:
                continue
        
        if not clips:
            return {"no_data": True}
        
        # Most active hour
        hour_counts = defaultdict(int)
        for c in clips:
            hour_counts[c["hour"]] += 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        peak_time = datetime.now().replace(hour=peak_hour, minute=0).strftime("%I %p")
        
        # Most active day
        day_counts = defaultdict(int)
        for c in clips:
            day_counts[c["day"]] += 1
        
        peak_day = max(day_counts.items(), key=lambda x: x[1])[0]
        
        # Most common activity
        type_counts = defaultdict(int)
        for c in clips:
            type_counts[c["type"]] += 1
        
        favorite_activity = max(type_counts.items(), key=lambda x: x[1])[0]
        
        return {
            "peak_time": peak_time,
            "peak_day": peak_day,
            "favorite_activity": favorite_activity.replace("_", " ").title(),
            "total_clips": len(clips),
        }


def get_mood_card() -> str:
    """Generate a text-based mood card for display."""
    analyzer = TankMoodAnalyzer()
    mood = analyzer.analyze_mood()
    favorites = analyzer.get_fish_favorites()
    
    lines = [
        f"╔══════════════════════════════╗",
        f"║   {mood.emoji} TANK MOOD: {mood.mood.upper():12} ║",
        f"╠══════════════════════════════╣",
        f"║ {mood.description:28} ║",
        f"║                              ║",
        f"║ Activity: {mood.activity_level:18} ║",
        f"║ Health:   {mood.health_vibe:18} ║",
    ]
    
    if not favorites.get("no_data"):
        lines.extend([
            f"║                              ║",
            f"║ Peak time: {favorites['peak_time']:16} ║",
            f"║ Peak day:  {favorites['peak_day']:16} ║",
        ])
    
    lines.append(f"╚══════════════════════════════╝")
    
    return "\n".join(lines)


def main():
    """CLI for tank mood."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check your tank's mood")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--heatmap", action="store_true", help="Show activity heatmap")
    
    args = parser.parse_args()
    analyzer = TankMoodAnalyzer()
    
    if args.heatmap:
        heatmap = analyzer.get_activity_heatmap()
        print("\n📊 Activity Heatmap (clips per hour)")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        print("     " + " ".join(f"{h:2}" for h in range(0, 24, 2)))
        for day in days:
            row = []
            for h in range(0, 24, 2):
                count = heatmap.get(day, {}).get(h, 0) + heatmap.get(day, {}).get(h+1, 0)
                if count == 0:
                    row.append(" ·")
                elif count < 3:
                    row.append(" ░")
                elif count < 5:
                    row.append(" ▒")
                else:
                    row.append(" █")
            print(f"{day}: {''.join(row)}")
        return
    
    if args.json:
        mood = analyzer.analyze_mood()
        favorites = analyzer.get_fish_favorites()
        print(json.dumps({
            "mood": mood.mood,
            "emoji": mood.emoji,
            "description": mood.description,
            "activity_level": mood.activity_level,
            "health_vibe": mood.health_vibe,
            "favorites": favorites,
        }, indent=2))
        return
    
    print(get_mood_card())


if __name__ == "__main__":
    main()
