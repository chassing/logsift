"""Tests for logfmt parser."""

from __future__ import annotations

from logdelve.models import LogLevel
from logdelve.parsers.logfmt import LogfmtParser


class TestLogfmtParserTryParse:
    def setup_method(self) -> None:
        self.parser = LogfmtParser()

    def test_basic_logfmt(self) -> None:
        result = self.parser.try_parse('time=2024-01-15T10:30:00Z level=info msg="request handled" service=api')
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.log_level == LogLevel.INFO
        assert result.content == "request handled"
        assert result.component == "api"

    def test_error_level(self) -> None:
        result = self.parser.try_parse('time=2024-01-15T10:30:00Z level=error msg="connection failed"')
        assert result is not None
        assert result.log_level == LogLevel.ERROR

    def test_ts_key(self) -> None:
        result = self.parser.try_parse('ts=2024-01-15T10:30:00Z level=info msg="ok"')
        assert result is not None
        assert result.timestamp is not None

    def test_no_time_key_returns_none(self) -> None:
        result = self.parser.try_parse('level=info msg="no time field"')
        assert result is None

    def test_single_pair_returns_none(self) -> None:
        result = self.parser.try_parse("time=2024-01-15T10:30:00Z")
        assert result is None

    def test_non_logfmt_returns_none(self) -> None:
        result = self.parser.try_parse("just regular text here")
        assert result is None

    def test_caller_as_component(self) -> None:
        result = self.parser.try_parse('time=2024-01-15T10:30:00Z level=info caller=main.go msg="started"')
        assert result is not None
        assert result.component == "main.go"

    def test_quoted_values(self) -> None:
        result = self.parser.try_parse('time=2024-01-15T10:30:00Z level=warn msg="slow query detected"')
        assert result is not None
        assert result.content == "slow query detected"
        assert result.log_level == LogLevel.WARN


class TestLogfmtParserParseLine:
    def setup_method(self) -> None:
        self.parser = LogfmtParser()

    def test_parse_line_logfmt(self) -> None:
        line = self.parser.parse_line(1, 'time=2024-01-15T10:30:00Z level=info msg="ok"')
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.log_level == LogLevel.INFO

    def test_parse_line_non_logfmt_fallback(self) -> None:
        line = self.parser.parse_line(2, "not logfmt")
        assert line.timestamp is None
