#!/usr/bin/env python3
"""
Highlights Reel Generator - Auto-compile best clips into a shareable video.
Perfect for social media content.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class ClipInfo:
    """Info about a clip for the highlight reel."""
    path: Path
    alert_type: str
    timestamp: datetime
    score: float  # Higher = more interesting
    is_cool_moment: bool


class HighlightsGenerator:
    """Generate highlight reels from accumulated clips."""
    
    # Scoring weights for different alert types
    INTEREST_SCORES = {
        "feeding_frenzy": 10,
        "fish_playing": 9,
        "interesting_moment": 8,
        "new_behavior": 8,
        "erratic_swimming": 6,  # Could be dramatic
        "motion_spike": 5,
        "fish_aggression": 7,
        "clustering": 4,
        "surface_activity": 3,
    }
    
    def __init__(self, clips_dir: str = "./clips", output_dir: str = "./highlights"):
        self.clips_dir = Path(clips_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_clips(self, days: int = 7) -> list[ClipInfo]:
        """Get all clips from the last N days."""
        clips = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for f in self.clips_dir.glob("*.mp4"):
            try:
                # Parse filename: 20260129_143022_feeding_frenzy.mp4
                parts = f.stem.split("_", 2)
                if len(parts) < 3:
                    continue
                    
                dt = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                if dt < cutoff:
                    continue
                    
                alert_type = parts[2]
                score = self.INTEREST_SCORES.get(alert_type, 1)
                is_cool = alert_type in ("feeding_frenzy", "fish_playing", "interesting_moment", "new_behavior")
                
                clips.append(ClipInfo(
                    path=f,
                    alert_type=alert_type,
                    timestamp=dt,
                    score=score,
                    is_cool_moment=is_cool,
                ))
            except Exception as e:
                print(f"[Highlights] Skipping {f.name}: {e}")
                continue
        
        return clips
    
    def select_highlights(self, clips: list[ClipInfo], 
                         max_clips: int = 10,
                         max_duration: int = 60) -> list[ClipInfo]:
        """Select the best clips for the highlight reel."""
        # Sort by score (descending) then by timestamp (most recent first)
        sorted_clips = sorted(clips, key=lambda c: (-c.score, -c.timestamp.timestamp()))
        
        # Take top clips
        selected = sorted_clips[:max_clips]
        
        # Re-sort by timestamp for chronological order in final video
        selected.sort(key=lambda c: c.timestamp)
        
        return selected
    
    def generate_reel(self, clips: Optional[list[ClipInfo]] = None,
                      days: int = 7,
                      max_clips: int = 10,
                      output_name: Optional[str] = None,
                      add_music: bool = False,
                      add_text_overlay: bool = True) -> Optional[Path]:
        """Generate a highlight reel video."""
        if clips is None:
            all_clips = self.get_clips(days=days)
            clips = self.select_highlights(all_clips, max_clips=max_clips)
        
        if not clips:
            print("[Highlights] No clips to compile")
            return None
        
        print(f"[Highlights] Compiling {len(clips)} clips...")
        
        # Output filename
        if output_name is None:
            output_name = f"highlights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = self.output_dir / output_name
        
        # Create concat file for ffmpeg
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for clip in clips:
                # Escape single quotes in path
                escaped_path = str(clip.path.absolute()).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
        ]
        
        # Add text overlay with timestamps if enabled
        if add_text_overlay:
            # Create filter for text overlay
            filter_parts = []
            for i, clip in enumerate(clips):
                time_str = clip.timestamp.strftime("%b %d, %I:%M %p")
                alert_str = clip.alert_type.replace("_", " ").title()
                # drawtext for each segment
                filter_parts.append(
                    f"drawtext=text='{time_str} - {alert_str}':"
                    f"fontsize=24:fontcolor=white:borderw=2:bordercolor=black:"
                    f"x=20:y=h-50:enable='between(t,{i*40},{(i+1)*40})'"
                )
            
            if filter_parts:
                cmd.extend(["-vf", ",".join(filter_parts)])
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path),
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[Highlights] ffmpeg error: {result.stderr}")
                return None
            
            # Cleanup
            concat_file.unlink(missing_ok=True)
            
            print(f"[Highlights] Created: {output_path}")
            print(f"[Highlights] Size: {output_path.stat().st_size / 1048576:.1f} MB")
            
            return output_path
            
        except FileNotFoundError:
            print("[Highlights] ffmpeg not found - install it first")
            return None
        except Exception as e:
            print(f"[Highlights] Error: {e}")
            return None
    
    def generate_gif(self, clip_path: str, 
                    output_path: Optional[str] = None,
                    start_sec: float = 0,
                    duration: float = 5,
                    width: int = 480,
                    fps: int = 15) -> Optional[Path]:
        """Generate a GIF from a clip - perfect for social media sharing."""
        clip = Path(clip_path)
        if not clip.exists():
            print(f"[Highlights] Clip not found: {clip_path}")
            return None
        
        if output_path is None:
            output_path = self.output_dir / f"{clip.stem}.gif"
        else:
            output_path = Path(output_path)
        
        # Two-pass GIF generation for better quality
        palette_path = self.output_dir / "palette.png"
        
        try:
            # Generate palette
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-t", str(duration),
                "-i", str(clip),
                "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,palettegen",
                str(palette_path),
            ], capture_output=True)
            
            # Generate GIF using palette
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-t", str(duration),
                "-i", str(clip),
                "-i", str(palette_path),
                "-filter_complex", f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse",
                str(output_path),
            ], capture_output=True)
            
            palette_path.unlink(missing_ok=True)
            
            if output_path.exists():
                print(f"[Highlights] GIF created: {output_path}")
                return output_path
            
        except FileNotFoundError:
            print("[Highlights] ffmpeg not found")
        except Exception as e:
            print(f"[Highlights] GIF error: {e}")
        
        return None
    
    def get_weekly_stats(self, days: int = 7) -> dict:
        """Get stats for the weekly highlight reel."""
        clips = self.get_clips(days=days)
        
        cool_moments = [c for c in clips if c.is_cool_moment]
        alerts = [c for c in clips if not c.is_cool_moment]
        
        # Count by type
        type_counts = {}
        for clip in clips:
            type_counts[clip.alert_type] = type_counts.get(clip.alert_type, 0) + 1
        
        # Most active day
        day_counts = {}
        for clip in clips:
            day = clip.timestamp.strftime("%A")
            day_counts[day] = day_counts.get(day, 0) + 1
        
        most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else "N/A"
        
        return {
            "total_clips": len(clips),
            "cool_moments": len(cool_moments),
            "alerts": len(alerts),
            "by_type": type_counts,
            "most_active_day": most_active_day,
            "period_days": days,
        }


def main():
    """CLI for highlight reel generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate fish tank highlight reels")
    parser.add_argument("--days", type=int, default=7, help="Look back N days")
    parser.add_argument("--max-clips", type=int, default=10, help="Max clips in reel")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--stats-only", action="store_true", help="Just show stats")
    parser.add_argument("--gif", type=str, help="Generate GIF from clip path")
    
    args = parser.parse_args()
    gen = HighlightsGenerator()
    
    if args.gif:
        gen.generate_gif(args.gif)
        return
    
    if args.stats_only:
        stats = gen.get_weekly_stats(days=args.days)
        print(f"\n📊 Weekly Stats ({stats['period_days']} days)")
        print(f"   Total clips: {stats['total_clips']}")
        print(f"   Cool moments: {stats['cool_moments']}")
        print(f"   Alerts: {stats['alerts']}")
        print(f"   Most active day: {stats['most_active_day']}")
        print(f"\n   By type:")
        for t, c in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            print(f"      {t.replace('_', ' ').title()}: {c}")
        return
    
    gen.generate_reel(days=args.days, max_clips=args.max_clips, output_name=args.output)


if __name__ == "__main__":
    main()
