"""Tests for the filter engine."""

from __future__ import annotations

from logdelve.filters import apply_filters
from logdelve.models import ContentType, FilterRule, FilterType, LogLine


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


JSON_LINES = [
    LogLine(
        line_number=1,
        raw='{"log_level": "info", "msg": "ok"}',
        content_type=ContentType.JSON,
        content='{"log_level": "info", "msg": "ok"}',
        parsed_json={"log_level": "info", "msg": "ok"},
    ),
    LogLine(
        line_number=2,
        raw='{"log_level": "error", "msg": "fail"}',
        content_type=ContentType.JSON,
        content='{"log_level": "error", "msg": "fail"}',
        parsed_json={"log_level": "error", "msg": "fail"},
    ),
    _make_line(3, "plain text no json"),
]


class TestJsonKeyFilters:
    def test_json_key_include(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="log_level=error",
                is_json_key=True,
                json_key="log_level",
                json_value="error",
            )
        ]
        result = apply_filters(JSON_LINES, rules)
        assert result == [1]

    def test_json_key_exclude(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.EXCLUDE,
                pattern="log_level=info",
                is_json_key=True,
                json_key="log_level",
                json_value="info",
            )
        ]
        result = apply_filters(JSON_LINES, rules)
        assert result == [1, 2]

    def test_json_key_no_match_on_text_line(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="log_level=info",
                is_json_key=True,
                json_key="log_level",
                json_value="info",
            )
        ]
        result = apply_filters(JSON_LINES, rules)
        # Only JSON line with matching key, not the text line
        assert result == [0]

    def test_mixed_text_and_json_filters(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="log_level=error",
                is_json_key=True,
                json_key="log_level",
                json_value="error",
            ),
            FilterRule(filter_type=FilterType.INCLUDE, pattern="plain"),
        ]
        result = apply_filters(JSON_LINES, rules)
        assert result == [1, 2]


def _make_component_line(line_number: int, raw: str, component: str | None) -> LogLine:
    return LogLine(
        line_number=line_number,
        raw=raw,
        content_type=ContentType.TEXT,
        content=raw,
        component=component,
    )


COMPONENT_LINES = [
    _make_component_line(1, "Starting api-server", "api-server"),
    _make_component_line(2, "Starting auth-service", "auth-service"),
    _make_component_line(3, "Health check ok", "api-server"),
    _make_component_line(4, "Login failed", "auth-service"),
    _make_component_line(5, "No component line", None),
    _make_component_line(6, "Worker started", "worker"),
]


class TestComponentFilters:
    def test_component_include(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:api-server",
                is_component=True,
                component_name="api-server",
            )
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        assert result == [0, 2]

    def test_component_exclude(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.EXCLUDE,
                pattern="component:auth-service",
                is_component=True,
                component_name="auth-service",
            )
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        assert result == [0, 2, 4, 5]

    def test_component_include_no_match_on_none(self) -> None:
        """Lines without a component don't match component include filters."""
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:api-server",
                is_component=True,
                component_name="api-server",
            )
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        # Line 5 (no component) is excluded because it doesn't match any include
        assert 4 not in result

    def test_multiple_component_includes_or_logic(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:api-server",
                is_component=True,
                component_name="api-server",
            ),
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:worker",
                is_component=True,
                component_name="worker",
            ),
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        assert result == [0, 2, 5]

    def test_component_filter_disabled(self) -> None:
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:api-server",
                is_component=True,
                component_name="api-server",
                enabled=False,
            )
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        assert result == [0, 1, 2, 3, 4, 5]

    def test_component_with_text_filter(self) -> None:
        """Component filter combined with text filter uses OR logic for includes."""
        rules = [
            FilterRule(
                filter_type=FilterType.INCLUDE,
                pattern="component:api-server",
                is_component=True,
                component_name="api-server",
            ),
            FilterRule(filter_type=FilterType.INCLUDE, pattern="Login"),
        ]
        result = apply_filters(COMPONENT_LINES, rules)
        # api-server lines (0, 2) + "Login failed" line (3)
        assert result == [0, 2, 3]
