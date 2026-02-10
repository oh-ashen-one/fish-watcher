"""
Fish Counter - Estimates number of fish visible in frame.
Uses background subtraction and blob detection.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class FishBlob:
    """Represents a detected fish blob."""
    x: int
    y: int
    width: int
    height: int
    area: int
    center: Tuple[int, int]


class FishCounter:
    """
    Counts fish using motion-based blob detection.
    
    Works by:
    1. Background subtraction to find moving objects
    2. Morphological operations to clean up noise
    3. Contour detection to find individual blobs
    4. Size filtering to identify fish-sized objects
    """
    
    def __init__(
        self,
        min_fish_area: int = 100,
        max_fish_area: int = 10000,
        learning_rate: float = 0.01,
        history: int = 500,
    ):
        """
        Initialize fish counter.
        
        Args:
            min_fish_area: Minimum blob area to consider as fish (pixels)
            max_fish_area: Maximum blob area to consider as fish (pixels)
            learning_rate: Background learning rate (0-1, lower = slower adaptation)
            history: Number of frames for background model
        """
        self.min_fish_area = min_fish_area
        self.max_fish_area = max_fish_area
        self.learning_rate = learning_rate
        
        # Background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=50,
            detectShadows=False
        )
        
        # Morphological kernels
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
        
        # Tracking history
        self.last_count = 0
        self.count_history: List[int] = []
        self.stable_count = 0
        
    def process(self, frame: np.ndarray) -> Tuple[int, List[FishBlob]]:
        """
        Process a frame and count fish.
        
        Args:
            frame: BGR image from camera
            
        Returns:
            Tuple of (fish_count, list_of_fish_blobs)
        """
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame, learningRate=self.learning_rate)
        
        # Morphological cleanup
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel_close)
        
        # Find contours
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter by size and create blobs
        fish_blobs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_fish_area <= area <= self.max_fish_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Aspect ratio filter (fish are roughly elongated)
                aspect = float(w) / h if h > 0 else 0
                if 0.2 <= aspect <= 5.0:  # Reasonable fish shapes
                    center = (x + w // 2, y + h // 2)
                    fish_blobs.append(FishBlob(
                        x=x, y=y, width=w, height=h,
                        area=area, center=center
                    ))
        
        # Update history and stable count
        count = len(fish_blobs)
        self.count_history.append(count)
        if len(self.count_history) > 30:
            self.count_history.pop(0)
        
        # Stable count is the mode of recent counts
        if self.count_history:
            from collections import Counter
            self.stable_count = Counter(self.count_history).most_common(1)[0][0]
        
        self.last_count = count
        return count, fish_blobs
    
    def draw_detections(
        self,
        frame: np.ndarray,
        blobs: List[FishBlob],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """
        Draw detection boxes and count on frame.
        
        Args:
            frame: BGR image
            blobs: List of detected fish blobs
            color: Box color (BGR)
            thickness: Line thickness
            
        Returns:
            Frame with drawings
        """
        output = frame.copy()
        
        # Draw boxes around fish
        for i, blob in enumerate(blobs):
            cv2.rectangle(
                output,
                (blob.x, blob.y),
                (blob.x + blob.width, blob.y + blob.height),
                color, thickness
            )
            # Label with number
            cv2.putText(
                output, f"#{i+1}",
                (blob.x, blob.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )
        
        # Draw count overlay
        count_text = f"Fish: {len(blobs)} (stable: {self.stable_count})"
        cv2.putText(
            output, count_text,
            (10, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
        )
        
        return output
    
    def get_stable_count(self) -> int:
        """Get the stable (mode) fish count."""
        return self.stable_count
    
    def reset(self) -> None:
        """Reset the background model and history."""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=False
        )
        self.count_history.clear()
        self.stable_count = 0


def count_fish_in_image(image_path: str) -> Tuple[int, List[FishBlob]]:
    """
    One-shot fish counting in a static image.
    Less accurate than video (no motion), uses color segmentation.
    """
    img = cv2.imread(image_path)
    if img is None:
        return 0, []
    
    # Convert to HSV for color segmentation
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Create mask for typical fish colors (this is a rough heuristic)
    # Orange/gold fish
    mask1 = cv2.inRange(hsv, (5, 100, 100), (25, 255, 255))
    # Blue fish
    mask2 = cv2.inRange(hsv, (100, 100, 100), (130, 255, 255))
    # Red fish
    mask3 = cv2.inRange(hsv, (0, 100, 100), (5, 255, 255))
    
    mask = mask1 | mask2 | mask3
    
    # Cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    fish_blobs = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if 100 <= area <= 10000:
            x, y, w, h = cv2.boundingRect(contour)
            aspect = float(w) / h if h > 0 else 0
            if 0.2 <= aspect <= 5.0:
                fish_blobs.append(FishBlob(
                    x=x, y=y, width=w, height=h,
                    area=area, center=(x + w // 2, y + h // 2)
                ))
    
    return len(fish_blobs), fish_blobs


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # Demo with webcam
        print("Usage: python -m src.fish_counter [camera_device|image_path]")
        print("\nRunning webcam demo (press 'q' to quit)...")
        
        cap = cv2.VideoCapture(0)
        counter = FishCounter()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            count, blobs = counter.process(frame)
            output = counter.draw_detections(frame, blobs)
            
            cv2.imshow("Fish Counter", output)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    else:
        path = sys.argv[1]
        
        # Check if it's an image or camera device
        if path.isdigit():
            device = int(path)
            print(f"Opening camera {device}...")
            cap = cv2.VideoCapture(device)
            counter = FishCounter()
            
            print("Press 'q' to quit")
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                count, blobs = counter.process(frame)
                output = counter.draw_detections(frame, blobs)
                
                cv2.imshow("Fish Counter", output)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
        else:
            # Image mode
            print(f"Analyzing image: {path}")
            count, blobs = count_fish_in_image(path)
            print(f"Detected {count} fish")
            
            for i, blob in enumerate(blobs):
                print(f"  Fish #{i+1}: pos=({blob.x},{blob.y}) size={blob.width}x{blob.height} area={blob.area}")
