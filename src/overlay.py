"""
AI Camera Overlay - Visual tracking UI for fish.
Draws bounding boxes, names, species, and stats on frames.
"""

import time
from dataclasses import dataclass
from typing import Optional
import numpy as np
import cv2


@dataclass
class FishProfile:
    """Fish profile from config."""
    name: str
    species: str
    description: str
    color: tuple = (0, 255, 0)  # BGR for bounding box


@dataclass
class TrackedFish:
    """A tracked fish in the frame."""
    id: int
    bbox: tuple  # (x, y, w, h)
    center: tuple  # (cx, cy)
    profile: Optional[FishProfile] = None
    status: str = "active"
    last_seen: float = 0
    velocity: float = 0


class FishTracker:
    """Simple fish tracking using contour detection."""
    
    def __init__(self, fish_profiles: list[dict] = None):
        self.profiles = []
        if fish_profiles:
            # Assign colors to each fish
            colors = [
                (0, 255, 0),    # Green
                (255, 165, 0),  # Orange
                (255, 0, 255),  # Magenta
                (0, 255, 255),  # Yellow
                (255, 0, 0),    # Blue
                (0, 165, 255),  # Orange
            ]
            for i, p in enumerate(fish_profiles):
                self.profiles.append(FishProfile(
                    name=p.get("name", f"Fish {i+1}"),
                    species=p.get("species", "Unknown"),
                    description=p.get("description", ""),
                    color=colors[i % len(colors)]
                ))
        
        self.tracked: list[TrackedFish] = []
        self.next_id = 1
        self.prev_gray = None
        
    def detect_fish(self, frame: np.ndarray) -> list[tuple]:
        """Detect fish-shaped objects in frame."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size and shape
        h, w = frame.shape[:2]
        min_area = (h * w) * 0.002  # 0.2% of frame
        max_area = (h * w) * 0.15   # 15% of frame
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, bw, bh = cv2.boundingRect(contour)
                # Fish are usually longer than tall
                aspect = bw / bh if bh > 0 else 0
                if 0.3 < aspect < 4.0:  # Reasonable fish aspect ratio
                    cx, cy = x + bw // 2, y + bh // 2
                    detections.append((x, y, bw, bh, cx, cy, area))
        
        return detections
    
    def update(self, frame: np.ndarray) -> list[TrackedFish]:
        """Update tracking with new frame."""
        detections = self.detect_fish(frame)
        now = time.time()
        
        # Simple tracking: match by closest distance
        used_detections = set()
        
        for tracked in self.tracked:
            best_dist = float('inf')
            best_det = None
            best_idx = -1
            
            for i, det in enumerate(detections):
                if i in used_detections:
                    continue
                x, y, bw, bh, cx, cy, area = det
                dist = np.sqrt((cx - tracked.center[0])**2 + (cy - tracked.center[1])**2)
                if dist < best_dist and dist < 100:  # Max 100px movement
                    best_dist = dist
                    best_det = det
                    best_idx = i
            
            if best_det:
                x, y, bw, bh, cx, cy, area = best_det
                # Calculate velocity
                if tracked.last_seen > 0:
                    dt = now - tracked.last_seen
                    if dt > 0:
                        tracked.velocity = best_dist / dt
                
                tracked.bbox = (x, y, bw, bh)
                tracked.center = (cx, cy)
                tracked.last_seen = now
                tracked.status = "active" if tracked.velocity > 5 else "resting"
                used_detections.add(best_idx)
            else:
                # Not seen - mark as hidden if too long
                if now - tracked.last_seen > 5:
                    tracked.status = "hidden"
        
        # Add new detections
        for i, det in enumerate(detections):
            if i not in used_detections:
                x, y, bw, bh, cx, cy, area = det
                
                # Assign profile if available
                profile = None
                if len(self.tracked) < len(self.profiles):
                    profile = self.profiles[len(self.tracked)]
                
                self.tracked.append(TrackedFish(
                    id=self.next_id,
                    bbox=(x, y, bw, bh),
                    center=(cx, cy),
                    profile=profile,
                    last_seen=now
                ))
                self.next_id += 1
        
        # Remove very old tracks
        self.tracked = [t for t in self.tracked if now - t.last_seen < 30]
        
        return self.tracked


class OverlayRenderer:
    """Renders AI overlay on frames."""
    
    def __init__(self, fish_profiles: list[dict] = None, tank_info: dict = None):
        self.tracker = FishTracker(fish_profiles)
        self.tank_info = tank_info or {}
        self.frame_count = 0
        self.start_time = time.time()
        
    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render overlay on frame."""
        self.frame_count += 1
        output = frame.copy()
        h, w = output.shape[:2]
        
        # Update tracking
        tracked = self.tracker.update(frame)
        
        # Draw fish boxes
        for fish in tracked:
            self._draw_fish_box(output, fish)
        
        # Draw header bar
        self._draw_header(output, len(tracked))
        
        # Draw stats panel
        self._draw_stats(output, tracked)
        
        return output
    
    def _draw_fish_box(self, frame: np.ndarray, fish: TrackedFish):
        """Draw bounding box and label for a fish."""
        x, y, bw, bh = fish.bbox
        
        # Get color from profile or default
        if fish.profile:
            color = fish.profile.color
            name = fish.profile.name
            species = fish.profile.species
        else:
            color = (0, 255, 0)
            name = f"Fish #{fish.id}"
            species = "Unknown"
        
        # Status color adjustment
        if fish.status == "hidden":
            color = (128, 128, 128)  # Gray for hidden
        elif fish.status == "resting":
            color = (255, 200, 0)  # Cyan-ish for resting
        
        # Draw box
        cv2.rectangle(frame, (x, y), (x + bw, y + bh), color, 2)
        
        # Draw corner accents (futuristic look)
        corner_len = min(bw, bh) // 4
        # Top-left
        cv2.line(frame, (x, y), (x + corner_len, y), color, 3)
        cv2.line(frame, (x, y), (x, y + corner_len), color, 3)
        # Top-right
        cv2.line(frame, (x + bw, y), (x + bw - corner_len, y), color, 3)
        cv2.line(frame, (x + bw, y), (x + bw, y + corner_len), color, 3)
        # Bottom-left
        cv2.line(frame, (x, y + bh), (x + corner_len, y + bh), color, 3)
        cv2.line(frame, (x, y + bh), (x, y + bh - corner_len), color, 3)
        # Bottom-right
        cv2.line(frame, (x + bw, y + bh), (x + bw - corner_len, y + bh), color, 3)
        cv2.line(frame, (x + bw, y + bh), (x + bw, y + bh - corner_len), color, 3)
        
        # Label background
        label = f"{name}"
        label2 = f"{species}"
        label3 = f"[{fish.status.upper()}]"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        
        # Label box above fish
        label_y = max(y - 50, 10)
        cv2.rectangle(frame, (x, label_y), (x + max(tw + 10, 120), label_y + 45), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, label_y), (x + max(tw + 10, 120), label_y + 45), color, 1)
        
        # Draw text
        cv2.putText(frame, label, (x + 5, label_y + 15), font, font_scale, color, thickness)
        cv2.putText(frame, label2, (x + 5, label_y + 30), font, 0.4, (200, 200, 200), 1)
        cv2.putText(frame, label3, (x + 5, label_y + 42), font, 0.35, self._status_color(fish.status), 1)
    
    def _status_color(self, status: str) -> tuple:
        """Get color for status text."""
        if status == "active":
            return (0, 255, 0)
        elif status == "resting":
            return (0, 255, 255)
        elif status == "hidden":
            return (128, 128, 128)
        return (255, 255, 255)
    
    def _draw_header(self, frame: np.ndarray, fish_count: int):
        """Draw header bar."""
        h, w = frame.shape[:2]
        
        # Header background
        cv2.rectangle(frame, (0, 0), (w, 35), (0, 0, 0), -1)
        cv2.line(frame, (0, 35), (w, 35), (0, 255, 0), 1)
        
        # Title
        cv2.putText(frame, "FISH WATCHER AI", (10, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Fish count
        cv2.putText(frame, f"TRACKING: {fish_count}", (w - 150, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Timestamp
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (w - 280, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    def _draw_stats(self, frame: np.ndarray, tracked: list[TrackedFish]):
        """Draw stats panel."""
        h, w = frame.shape[:2]
        
        # Stats box in bottom-left
        box_h = 80
        box_w = 200
        
        cv2.rectangle(frame, (5, h - box_h - 5), (box_w, h - 5), (0, 0, 0), -1)
        cv2.rectangle(frame, (5, h - box_h - 5), (box_w, h - 5), (0, 255, 0), 1)
        
        # Runtime
        runtime = int(time.time() - self.start_time)
        runtime_str = f"{runtime // 3600:02d}:{(runtime % 3600) // 60:02d}:{runtime % 60:02d}"
        
        cv2.putText(frame, f"RUNTIME: {runtime_str}", (10, h - box_h + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        cv2.putText(frame, f"FRAMES: {self.frame_count}", (10, h - box_h + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Tank info
        tank_type = self.tank_info.get("type", "freshwater").upper()
        tank_size = self.tank_info.get("size", "")
        cv2.putText(frame, f"TANK: {tank_size} {tank_type}", (10, h - box_h + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Status counts
        active = sum(1 for t in tracked if t.status == "active")
        resting = sum(1 for t in tracked if t.status == "resting")
        cv2.putText(frame, f"ACTIVE: {active}  REST: {resting}", (10, h - box_h + 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)


def create_overlay_frame(frame: np.ndarray, fish_profiles: list = None, tank_info: dict = None) -> np.ndarray:
    """One-shot function to add overlay to a single frame."""
    renderer = OverlayRenderer(fish_profiles, tank_info)
    return renderer.render(frame)
