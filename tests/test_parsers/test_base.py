"""Tests for shared parser utilities."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers import classify_content, extract_component_from_json, extract_log_level


class TestClassifyContent:
    def test_json_object(self) -> None:
        content_type, parsed = classify_content('{"key": "value", "num": 42}')
        assert content_type == ContentType.JSON
        assert parsed is not None
        assert parsed["key"] == "value"
        assert parsed["num"] == 42

    def test_plain_text(self) -> None:
        content_type, parsed = classify_content("just plain text here")
        assert content_type == ContentType.TEXT
        assert parsed is None

    def test_invalid_json(self) -> None:
        content_type, parsed = classify_content("{not valid json}")
        assert content_type == ContentType.TEXT
        assert parsed is None

    def test_json_with_whitespace(self) -> None:
        content_type, parsed = classify_content('  {"key": "value"}  ')
        assert content_type == ContentType.JSON
        assert parsed is not None

    def test_json_array_not_matched(self) -> None:
        content_type, parsed = classify_content("[1, 2, 3]")
        assert content_type == ContentType.TEXT
        assert parsed is None

    def test_empty_string(self) -> None:
        content_type, parsed = classify_content("")
        assert content_type == ContentType.TEXT
        assert parsed is None


class TestExtractLogLevel:
    def test_json_log_level(self) -> None:
        assert extract_log_level("", {"log_level": "info"}) == LogLevel.INFO

    def test_json_level(self) -> None:
        assert extract_log_level("", {"level": "warning"}) == LogLevel.WARN

    def test_json_severity(self) -> None:
        assert extract_log_level("", {"severity": "critical"}) == LogLevel.FATAL

    def test_json_case_insensitive(self) -> None:
        assert extract_log_level("", {"level": "ERROR"}) == LogLevel.ERROR

    def test_bracket_pattern(self) -> None:
        assert extract_log_level("[ERROR] something failed", None) == LogLevel.ERROR

    def test_bracket_warn(self) -> None:
        assert extract_log_level("[WARNING] slow query", None) == LogLevel.WARN

    def test_word_pattern(self) -> None:
        assert extract_log_level("ERROR connection refused", None) == LogLevel.ERROR

    def test_kv_pattern(self) -> None:
        assert extract_log_level("level=error msg=fail", None) == LogLevel.ERROR

    def test_debug(self) -> None:
        assert extract_log_level("", {"level": "debug"}) == LogLevel.DEBUG

    def test_trace(self) -> None:
        assert extract_log_level("", {"level": "trace"}) == LogLevel.TRACE

    def test_no_level(self) -> None:
        assert extract_log_level("just some text", None) is None

    def test_json_priority_over_text(self) -> None:
        assert extract_log_level("[ERROR] text", {"level": "info"}) == LogLevel.INFO

    def test_heuristic_fail(self) -> None:
        assert extract_log_level("connection refused by server", None) == LogLevel.ERROR

    def test_heuristic_deprecated(self) -> None:
        assert extract_log_level("deprecated method called", None) == LogLevel.WARN


class TestExtractComponentFromJson:
    def test_service(self) -> None:
        assert extract_component_from_json({"service": "api"}) == "api"

    def test_component(self) -> None:
        assert extract_component_from_json({"component": "worker"}) == "worker"

    def test_priority_order(self) -> None:
        assert extract_component_from_json({"service": "svc", "component": "comp"}) == "svc"

    def test_no_component(self) -> None:
        assert extract_component_from_json({"key": "val"}) is None

    def test_none_json(self) -> None:
        assert extract_component_from_json(None) is None

    def test_non_string_ignored(self) -> None:
        assert extract_component_from_json({"service": 123}) is None
