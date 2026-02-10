"""Tests for src.vision — Claude vision integration."""

import json
import numpy as np
import pytest

from src.vision import ClaudeVisionAnalyzer, VisionAnalysis


class TestVisionAnalysis:
    def test_dataclass_fields(self) -> None:
        va = VisionAnalysis(
            summary="All good",
            health_concerns=[],
            observations=["Fish swimming"],
            recommendations=[],
            severity="normal",
            confidence=0.85,
        )
        assert va.severity == "normal"
        assert va.raw_response is None


class TestClaudeVisionAnalyzer:
    def test_init_no_api_key(self) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key=None)
        # Should fall back to env or CLI
        assert analyzer.model == "claude-sonnet-4-20250514"

    def test_analyze_frame_none(self) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        result = analyzer.analyze_frame(None)
        assert result is None

    def test_analyze_image_path_missing(self, tmp_path) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        result = analyzer.analyze_image_path(str(tmp_path / "nope.jpg"))
        assert result is None

    def test_analyze_clip_missing(self, tmp_path) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        result = analyzer.analyze_clip(str(tmp_path / "nope.mp4"))
        assert result is None

    def test_parse_response_valid_json(self) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        data = {
            "summary": "Healthy tank",
            "health_concerns": [],
            "observations": ["Clear water"],
            "recommendations": [],
            "severity": "normal",
        }
        result = analyzer._parse_response(json.dumps(data))
        assert result is not None
        assert result.summary == "Healthy tank"
        assert result.severity == "normal"
        assert result.confidence == 0.85

    def test_parse_response_code_block(self) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        data = {
            "summary": "OK",
            "health_concerns": [],
            "observations": [],
            "recommendations": [],
            "severity": "normal",
        }
        text = f"```json\n{json.dumps(data)}\n```"
        result = analyzer._parse_response(text)
        assert result is not None
        assert result.summary == "OK"

    def test_parse_response_invalid_json(self) -> None:
        analyzer = ClaudeVisionAnalyzer(api_key="fake")
        result = analyzer._parse_response("not json at all")
        assert result is not None
        assert result.confidence == 0.5  # Degraded confidence
        assert "not json" in result.summary
