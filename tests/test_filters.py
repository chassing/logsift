"""Tests for the filter engine."""

from __future__ import annotations

from logsift.filters import apply_filters
from logsift.models import ContentType, FilterRule, FilterType, LogLine


def _make_line(line_number: int, raw: str) -> LogLine:
    return LogLine(
        line_number=line_number,
        raw=raw,
        content_type=ContentType.TEXT,
        content=raw,
    )


SAMPLE_LINES = [
    _make_line(1, "2024-01-15 ERROR: Connection failed"),
    _make_line(2, "2024-01-15 INFO: Server started"),
    _make_line(3, "2024-01-15 DEBUG: Processing request"),
    _make_line(4, "2024-01-15 ERROR: Timeout occurred"),
    _make_line(5, "2024-01-15 INFO: Request completed"),
    _make_line(6, "2024-01-15 WARN: High memory usage"),
]


class TestApplyFilters:
    def test_no_filters_returns_all(self) -> None:
        result = apply_filters(SAMPLE_LINES, [])
        assert result == [0, 1, 2, 3, 4, 5]

    def test_include_filter(self) -> None:
        rules = [FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [0, 3]

    def test_exclude_filter(self) -> None:
        rules = [FilterRule(filter_type=FilterType.EXCLUDE, pattern="ERROR")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [1, 2, 4, 5]

    def test_include_case_insensitive(self) -> None:
        rules = [FilterRule(filter_type=FilterType.INCLUDE, pattern="error")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [0, 3]

    def test_exclude_case_insensitive(self) -> None:
        rules = [FilterRule(filter_type=FilterType.EXCLUDE, pattern="error")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [1, 2, 4, 5]

    def test_multiple_includes_or_logic(self) -> None:
        rules = [
            FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR"),
            FilterRule(filter_type=FilterType.INCLUDE, pattern="WARN"),
        ]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [0, 3, 5]

    def test_include_plus_exclude(self) -> None:
        rules = [
            FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR"),
            FilterRule(filter_type=FilterType.EXCLUDE, pattern="Timeout"),
        ]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [0]

    def test_disabled_filter_ignored(self) -> None:
        rules = [FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR", enabled=False)]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == [0, 1, 2, 3, 4, 5]

    def test_no_matches_returns_empty(self) -> None:
        rules = [FilterRule(filter_type=FilterType.INCLUDE, pattern="NONEXISTENT")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == []

    def test_exclude_all_returns_empty(self) -> None:
        rules = [FilterRule(filter_type=FilterType.EXCLUDE, pattern="2024")]
        result = apply_filters(SAMPLE_LINES, rules)
        assert result == []

    def test_empty_lines_no_filters(self) -> None:
        result = apply_filters([], [])
        assert result == []

    def test_mixed_enabled_disabled(self) -> None:
        rules = [
            FilterRule(filter_type=FilterType.INCLUDE, pattern="ERROR", enabled=True),
            FilterRule(filter_type=FilterType.INCLUDE, pattern="INFO", enabled=False),
        ]
        result = apply_filters(SAMPLE_LINES, rules)
        # Only ERROR include is active
        assert result == [0, 3]
