"""
Claude Vision integration for intelligent fish tank analysis.
Uses Claude to analyze clips and provide detailed assessments.
"""

import os
import json
import base64
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import cv2


@dataclass
class VisionAnalysis:
    """Result of Claude vision analysis."""
    summary: str
    health_concerns: list[str]
    observations: list[str]
    recommendations: list[str]
    severity: str  # "normal", "minor", "moderate", "serious", "critical"
    confidence: float
    raw_response: Optional[str] = None


class ClaudeVisionAnalyzer:
    """Analyzes fish tank frames/clips using Claude's vision capabilities."""
    
    ANALYSIS_PROMPT = """You are a fish health expert analyzing a fish tank camera feed.

Analyze this image and provide:
1. **Summary**: One sentence describing what you see
2. **Health concerns**: Any potential health issues with the fish (empty list if none)
3. **Observations**: Notable observations about the tank/fish
4. **Recommendations**: Actionable suggestions (empty list if none)
5. **Severity**: Overall assessment - one of: normal, minor, moderate, serious, critical

Be concise but thorough. Focus on:
- Fish behavior (swimming patterns, activity level, position in tank)
- Physical appearance (colors, fins, eyes, body shape)
- Tank conditions (water clarity, decorations, equipment)
- Signs of stress or illness

Respond ONLY with valid JSON in this exact format:
{
    "summary": "...",
    "health_concerns": ["...", "..."],
    "observations": ["...", "..."],
    "recommendations": ["...", "..."],
    "severity": "normal|minor|moderate|serious|critical"
}"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        
    def analyze_frame(self, frame) -> Optional[VisionAnalysis]:
        """Analyze a single frame (numpy array from OpenCV)."""
        if frame is None:
            return None
            
        # Encode frame as JPEG then base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return self._call_claude(image_b64)
    
    def analyze_image_path(self, image_path: str) -> Optional[VisionAnalysis]:
        """Analyze an image file."""
        path = Path(image_path)
        if not path.exists():
            return None
            
        with open(path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        return self._call_claude(image_b64)
    
    def analyze_clip(self, clip_path: str, sample_frames: int = 3) -> Optional[VisionAnalysis]:
        """Analyze a video clip by sampling frames.
        
        Args:
            clip_path: Path to video file
            sample_frames: Number of frames to sample (default 3: start, middle, end)
        """
        path = Path(clip_path)
        if not path.exists():
            return None
            
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return None
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < sample_frames:
            sample_frames = total_frames
            
        # Calculate frame positions to sample
        positions = [int(total_frames * i / (sample_frames - 1)) for i in range(sample_frames)] if sample_frames > 1 else [0]
        
        frames = []
        for pos in positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()
        
        if not frames:
            return None
            
        # Analyze the middle frame (most representative)
        middle_idx = len(frames) // 2
        return self.analyze_frame(frames[middle_idx])
    
    def _call_claude(self, image_b64: str) -> Optional[VisionAnalysis]:
        """Call Claude API with the image."""
        if not self.api_key:
            # Fall back to CLI if no API key
            return self._call_claude_cli(image_b64)
            
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": self.ANALYSIS_PROMPT,
                            },
                        ],
                    }
                ],
            )
            
            return self._parse_response(response.content[0].text)
            
        except ImportError:
            # anthropic package not installed, fall back to CLI
            return self._call_claude_cli(image_b64)
        except Exception as e:
            print(f"[Vision] API error: {e}")
            return None
    
    def _call_claude_cli(self, image_b64: str) -> Optional[VisionAnalysis]:
        """Use claude CLI as fallback."""
        try:
            # Write image to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(base64.b64decode(image_b64))
                temp_path = f.name
            
            # Call claude CLI with image
            result = subprocess.run(
                ['claude', '--image', temp_path, '--output-format', 'text', '-p', self.ANALYSIS_PROMPT],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            # Clean up
            os.unlink(temp_path)
            
            if result.returncode == 0:
                return self._parse_response(result.stdout)
            else:
                print(f"[Vision] CLI error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"[Vision] CLI fallback error: {e}")
            return None
    
    def _parse_response(self, text: str) -> Optional[VisionAnalysis]:
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            text = text.strip()
            if text.startswith('```'):
                # Remove code block markers
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1])
            
            data = json.loads(text)
            
            return VisionAnalysis(
                summary=data.get("summary", "Analysis complete"),
                health_concerns=data.get("health_concerns", []),
                observations=data.get("observations", []),
                recommendations=data.get("recommendations", []),
                severity=data.get("severity", "normal"),
                confidence=0.85,  # Default confidence for vision analysis
                raw_response=text,
            )
            
        except json.JSONDecodeError as e:
            print(f"[Vision] Failed to parse response: {e}")
            # Return basic analysis from text
            return VisionAnalysis(
                summary=text[:200] if text else "Analysis failed",
                health_concerns=[],
                observations=[],
                recommendations=[],
                severity="normal",
                confidence=0.5,
                raw_response=text,
            )


def analyze_for_clawdbot(clip_path: str) -> dict:
    """Convenience function for Clawdbot integration.
    
    Returns a dict suitable for including in alerts.
    """
    analyzer = ClaudeVisionAnalyzer()
    result = analyzer.analyze_clip(clip_path)
    
    if not result:
        return {"error": "Vision analysis failed"}
    
    return {
        "summary": result.summary,
        "health_concerns": result.health_concerns,
        "observations": result.observations,
        "recommendations": result.recommendations,
        "severity": result.severity,
        "confidence": result.confidence,
    }


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.vision <image_or_clip_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    print(f"Analyzing: {path}")
    
    analyzer = ClaudeVisionAnalyzer()
    
    if path.endswith(('.mp4', '.avi', '.mov')):
        result = analyzer.analyze_clip(path)
    else:
        result = analyzer.analyze_image_path(path)
    
    if result:
        print("\n📊 Analysis Results:")
        print(f"   Summary: {result.summary}")
        print(f"   Severity: {result.severity}")
        if result.health_concerns:
            print("   ⚠️ Health concerns:")
            for c in result.health_concerns:
                print(f"      - {c}")
        if result.observations:
            print("   👁️ Observations:")
            for o in result.observations:
                print(f"      - {o}")
        if result.recommendations:
            print("   💡 Recommendations:")
            for r in result.recommendations:
                print(f"      - {r}")
    else:
        print("Analysis failed")
