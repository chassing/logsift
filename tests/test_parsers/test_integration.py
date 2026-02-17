"""Integration tests for end-to-end log line parsing via AutoParser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel, LogLine
from logdelve.parsers import ParserName, get_parser


def _parse_line(line_number: int, raw: str) -> LogLine:
    return get_parser(ParserName.AUTO).parse_line(line_number, raw)


class TestParseLine:
    def test_full_json_line(self) -> None:
        line = _parse_line(1, '2024-01-15T10:30:00Z {"log_level": "info", "message": "ok"}')
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.timestamp.year == 2024
        assert line.content_type == ContentType.JSON
        assert line.parsed_json is not None
        assert line.parsed_json["log_level"] == "info"

    def test_full_text_line(self) -> None:
        line = _parse_line(2, "2024-01-15T10:30:01Z Connection established")
        assert line.line_number == 2
        assert line.timestamp is not None
        assert line.content_type == ContentType.TEXT
        assert line.parsed_json is None
        assert line.content == "Connection established"

    def test_no_timestamp_text(self) -> None:
        line = _parse_line(3, "Just some text")
        assert line.line_number == 3
        assert line.timestamp is None
        assert line.content_type == ContentType.TEXT
        assert line.content == "Just some text"

    def test_no_timestamp_json(self) -> None:
        line = _parse_line(4, '{"key": "value"}')
        assert line.line_number == 4
        assert line.timestamp is None
        assert line.content_type == ContentType.JSON
        assert line.parsed_json is not None

    def test_empty_line(self) -> None:
        line = _parse_line(5, "")
        assert line.line_number == 5
        assert line.timestamp is None
        assert line.content_type == ContentType.TEXT
        assert line.content == ""

    def test_raw_preserved(self) -> None:
        raw = '2024-01-15T10:30:00Z {"key": "value"}'
        line = _parse_line(1, raw)
        assert line.raw == raw

    def test_json_log_level(self) -> None:
        line = _parse_line(1, '2024-01-15T10:30:00Z {"log_level": "error", "msg": "fail"}')
        assert line.log_level == LogLevel.ERROR

    def test_text_log_level(self) -> None:
        line = _parse_line(1, "2024-01-15T10:30:00Z [ERROR] something broke")
        assert line.log_level == LogLevel.ERROR

    def test_component_from_bracket_prefix(self) -> None:
        line = _parse_line(1, "[my-pod-abc123] 2024-01-15T10:30:00Z some message")
        assert line.component == "my-pod-abc123"
        assert line.timestamp is not None

    def test_component_from_json(self) -> None:
        line = _parse_line(1, '2024-01-15T10:30:00Z {"service": "api-gateway", "msg": "ok"}')
        assert line.component == "api-gateway"
