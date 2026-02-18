"""Tests for baseline comparison and anomaly detection."""

from __future__ import annotations

import pytest

from logdelve.anomaly import build_baseline, detect_anomalies
from logdelve.models import ContentType, LogLine


def _make_line(
    content: str,
    line_number: int = 1,
    content_type: ContentType = ContentType.TEXT,
    parsed_json: dict | None = None,
) -> LogLine:
    return LogLine(
        line_number=line_number,
        raw=content,
        content_type=content_type,
        parsed_json=parsed_json,
    )


class TestBuildBaseline:
    def test_builds_template_hashes(self) -> None:
        lines = [
            _make_line("Connection from 192.168.1.1 established", line_number=1),
            _make_line("Connection from 192.168.1.2 established", line_number=2),
            _make_line("Health check passed", line_number=3),
        ]
        baseline = build_baseline(lines)
        assert len(baseline.template_hashes) == 2
        assert baseline.total_lines == 3

    def test_empty_baseline(self) -> None:
        baseline = build_baseline([])
        assert len(baseline.template_hashes) == 0
        assert baseline.total_lines == 0

    def test_tracks_counts(self) -> None:
        lines = [
            _make_line("Event A", line_number=1),
            _make_line("Event A", line_number=2),
            _make_line("Event B", line_number=3),
        ]
        baseline = build_baseline(lines)
        assert sum(baseline.template_counts.values()) == 3


class TestDetectAnomalies:
    def test_no_anomalies_identical(self) -> None:
        lines = [
            _make_line("Health check passed", line_number=1),
            _make_line("Health check passed", line_number=2),
        ]
        baseline = build_baseline(lines)
        result = detect_anomalies(lines, baseline)
        assert result.anomaly_count == 0
        assert len(result.novel_templates) == 0

    def test_detects_novel_templates(self) -> None:
        baseline_lines = [
            _make_line("Health check passed", line_number=1),
            _make_line("Request processed", line_number=2),
        ]
        current_lines = [
            _make_line("Health check passed", line_number=1),
            _make_line("Connection refused to 10.0.0.1", line_number=2),
            _make_line("Connection refused to 10.0.0.2", line_number=3),
        ]
        baseline = build_baseline(baseline_lines)
        result = detect_anomalies(current_lines, baseline)
        assert len(result.novel_templates) >= 1
        assert result.anomaly_count >= 2  # The two "Connection refused" lines

    def test_novel_lines_score_1(self) -> None:
        baseline_lines = [_make_line("Normal event", line_number=1)]
        current_lines = [
            _make_line("Normal event", line_number=1),
            _make_line("NEW ERROR: something broke", line_number=2),
        ]
        baseline = build_baseline(baseline_lines)
        result = detect_anomalies(current_lines, baseline)
        assert result.scores.get(1, 0) == pytest.approx(1.0)  # Line index 1 is novel
        assert 0 not in result.scores  # Line index 0 is known

    def test_disappeared_templates(self) -> None:
        baseline_lines = [
            _make_line("Service A running", line_number=1),
            _make_line("Service B running", line_number=2),
        ]
        current_lines = [
            _make_line("Service A running", line_number=1),
        ]
        baseline = build_baseline(baseline_lines)
        result = detect_anomalies(current_lines, baseline)
        assert len(result.disappeared_hashes) >= 1

    def test_empty_current(self) -> None:
        baseline_lines = [_make_line("Event", line_number=1)]
        baseline = build_baseline(baseline_lines)
        result = detect_anomalies([], baseline)
        assert result.anomaly_count == 0
        assert len(result.disappeared_hashes) >= 1

    def test_empty_baseline_all_novel(self) -> None:
        baseline = build_baseline([])
        current_lines = [
            _make_line("Event A", line_number=1),
            _make_line("Event B", line_number=2),
        ]
        result = detect_anomalies(current_lines, baseline)
        assert result.anomaly_count == 2
        assert len(result.novel_templates) == 2

    def test_json_templates(self) -> None:
        baseline_lines = [
            _make_line(
                '{"event": "Request OK"}',
                line_number=1,
                content_type=ContentType.JSON,
                parsed_json={"event": "Request OK"},
            ),
        ]
        current_lines = [
            _make_line(
                '{"event": "Request OK"}',
                line_number=1,
                content_type=ContentType.JSON,
                parsed_json={"event": "Request OK"},
            ),
            _make_line(
                '{"event": "Database timeout"}',
                line_number=2,
                content_type=ContentType.JSON,
                parsed_json={"event": "Database timeout"},
            ),
        ]
        baseline = build_baseline(baseline_lines)
        result = detect_anomalies(current_lines, baseline)
        assert result.anomaly_count >= 1
        assert result.scores.get(1, 0) == pytest.approx(1.0)
