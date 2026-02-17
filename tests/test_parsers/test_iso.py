"""Tests for ISO 8601 parser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.iso import IsoParser


class TestIsoParserTryParse:
    def setup_method(self) -> None:
        self.parser = IsoParser()

    def test_iso_with_z(self) -> None:
        result = self.parser.try_parse('2024-01-15T10:30:00Z {"key": "value"}')
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.timestamp.month == 1
        assert result.timestamp.day == 15
        assert result.content == '{"key": "value"}'

    def test_iso_with_space(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:02.123 some text")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.content == "some text"

    def test_iso_with_timezone_offset(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:06+02:00 content here")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.tzinfo is not None
        assert result.content == "content here"

    def test_slash_date(self) -> None:
        result = self.parser.try_parse("2024/01/15 10:30:05 Simple log entry")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.content == "Simple log entry"

    def test_non_iso_returns_none(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 syslog line")
        assert result is None

    def test_no_timestamp_returns_none(self) -> None:
        result = self.parser.try_parse("just plain text")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = self.parser.try_parse("")
        assert result is None

    def test_json_content_classified(self) -> None:
        result = self.parser.try_parse('2024-01-15T10:30:00Z {"level": "error", "msg": "fail"}')
        assert result is not None
        assert result.content_type == ContentType.JSON
        assert result.parsed_json is not None
        assert result.log_level == LogLevel.ERROR

    def test_component_from_json(self) -> None:
        result = self.parser.try_parse('2024-01-15T10:30:00Z {"service": "api", "msg": "ok"}')
        assert result is not None
        assert result.component == "api"


class TestIsoParserParseLine:
    def setup_method(self) -> None:
        self.parser = IsoParser()

    def test_parse_line_iso(self) -> None:
        line = self.parser.parse_line(1, "2024-01-15T10:30:00Z some message")
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.content == "some message"
        assert line.log_level == LogLevel.INFO

    def test_parse_line_no_match_fallback(self) -> None:
        line = self.parser.parse_line(2, "just text")
        assert line.line_number == 2
        assert line.timestamp is None
        assert line.content == "just text"

    def test_raw_preserved(self) -> None:
        raw = "2024-01-15T10:30:00Z test"
        line = self.parser.parse_line(1, raw)
        assert line.raw == raw
