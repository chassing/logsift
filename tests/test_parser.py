"""Tests for log line parsing."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parser import extract_component, extract_timestamp, parse_line
from logdelve.parsers.base import classify_content, extract_log_level


class TestExtractTimestamp:
    def test_iso8601_with_z(self) -> None:
        ts, remainder = extract_timestamp('2024-01-15T10:30:00Z {"key": "value"}')
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert ts.hour == 10
        assert ts.minute == 30
        assert ts.second == 0
        assert remainder == '{"key": "value"}'

    def test_iso8601_with_space(self) -> None:
        ts, remainder = extract_timestamp("2024-01-15 10:30:02.123 some text")
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert remainder == "some text"

    def test_iso8601_with_timezone_offset(self) -> None:
        ts, remainder = extract_timestamp("2024-01-15T10:30:06+02:00 content here")
        assert ts is not None
        assert ts.year == 2024
        assert ts.tzinfo is not None
        assert remainder == "content here"

    def test_syslog_format(self) -> None:
        ts, remainder = extract_timestamp("Jan 15 10:30:03 myhost syslogd: restart")
        assert ts is not None
        assert ts.month == 1
        assert ts.day == 15
        assert ts.hour == 10
        assert ts.minute == 30
        assert ts.second == 3
        assert remainder == "myhost syslogd: restart"

    def test_syslog_single_digit_day(self) -> None:
        ts, remainder = extract_timestamp("Jan  5 10:30:03 myhost syslogd: restart")
        assert ts is not None
        assert ts.day == 5
        assert remainder == "myhost syslogd: restart"

    def test_apache_clf(self) -> None:
        ts, remainder = extract_timestamp('[15/Jan/2024:10:30:04 +0000] "GET /api/health HTTP/1.1" 200 15')
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert remainder == '"GET /api/health HTTP/1.1" 200 15'

    def test_slash_date(self) -> None:
        ts, remainder = extract_timestamp("2024/01/15 10:30:05 Simple log entry")
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert remainder == "Simple log entry"

    def test_no_timestamp(self) -> None:
        ts, remainder = extract_timestamp("No timestamp here, just plain text")
        assert ts is None
        assert remainder == "No timestamp here, just plain text"

    def test_empty_string(self) -> None:
        ts, remainder = extract_timestamp("")
        assert ts is None
        assert remainder == ""


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
        assert parsed["key"] == "value"

    def test_json_array_not_matched(self) -> None:
        """Arrays are not treated as JSON log content (only objects)."""
        content_type, parsed = classify_content("[1, 2, 3]")
        assert content_type == ContentType.TEXT
        assert parsed is None

    def test_empty_string(self) -> None:
        content_type, parsed = classify_content("")
        assert content_type == ContentType.TEXT
        assert parsed is None


class TestParseLine:
    def test_full_json_line(self) -> None:
        line = parse_line(1, '2024-01-15T10:30:00Z {"log_level": "info", "message": "ok"}')
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.timestamp.year == 2024
        assert line.content_type == ContentType.JSON
        assert line.parsed_json is not None
        assert line.parsed_json["log_level"] == "info"

    def test_full_text_line(self) -> None:
        line = parse_line(2, "2024-01-15T10:30:01Z Connection established")
        assert line.line_number == 2
        assert line.timestamp is not None
        assert line.content_type == ContentType.TEXT
        assert line.parsed_json is None
        assert line.content == "Connection established"

    def test_no_timestamp_text(self) -> None:
        line = parse_line(3, "Just some text")
        assert line.line_number == 3
        assert line.timestamp is None
        assert line.content_type == ContentType.TEXT
        assert line.content == "Just some text"

    def test_no_timestamp_json(self) -> None:
        line = parse_line(4, '{"key": "value"}')
        assert line.line_number == 4
        assert line.timestamp is None
        assert line.content_type == ContentType.JSON
        assert line.parsed_json is not None

    def test_empty_line(self) -> None:
        line = parse_line(5, "")
        assert line.line_number == 5
        assert line.timestamp is None
        assert line.content_type == ContentType.TEXT
        assert line.content == ""

    def test_raw_preserved(self) -> None:
        raw = '2024-01-15T10:30:00Z {"key": "value"}'
        line = parse_line(1, raw)
        assert line.raw == raw

    def test_json_log_level(self) -> None:
        line = parse_line(1, '2024-01-15T10:30:00Z {"log_level": "error", "msg": "fail"}')
        assert line.log_level == LogLevel.ERROR

    def test_text_log_level(self) -> None:
        line = parse_line(1, "2024-01-15T10:30:00Z [ERROR] something broke")
        assert line.log_level == LogLevel.ERROR

    def test_component_from_bracket_prefix(self) -> None:
        line = parse_line(1, "[my-pod-abc123] 2024-01-15T10:30:00Z some message")
        assert line.component == "my-pod-abc123"
        assert line.timestamp is not None

    def test_component_from_json(self) -> None:
        line = parse_line(1, '2024-01-15T10:30:00Z {"service": "api-gateway", "msg": "ok"}')
        assert line.component == "api-gateway"


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


class TestExtractComponent:
    def test_docker_compose(self) -> None:
        assert extract_component("web-service  | some log", None) == "web-service"

    def test_k8s_bracket(self) -> None:
        assert extract_component("[my-pod-abc123] log msg", None) == "my-pod-abc123"

    def test_json_service(self) -> None:
        assert extract_component("some line", {"service": "api"}) == "api"

    def test_json_component(self) -> None:
        assert extract_component("some line", {"component": "worker"}) == "worker"

    def test_no_component(self) -> None:
        assert extract_component("just text", None) is None

    def test_json_field_priority(self) -> None:
        assert extract_component("some line", {"service": "svc", "component": "comp"}) == "svc"
