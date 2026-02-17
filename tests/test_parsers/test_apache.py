"""Tests for Apache CLF parser."""

from __future__ import annotations

from logdelve.models import LogLevel
from logdelve.parsers.apache import ApacheParser


class TestApacheParserTryParse:
    def setup_method(self) -> None:
        self.parser = ApacheParser()

    def test_basic_apache_clf(self) -> None:
        result = self.parser.try_parse('[15/Jan/2024:10:30:04 +0000] "GET /api/health HTTP/1.1" 200 15')
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.timestamp.month == 1
        assert result.timestamp.day == 15
        assert result.timestamp.hour == 10
        assert result.content == '"GET /api/health HTTP/1.1" 200 15'

    def test_negative_timezone(self) -> None:
        result = self.parser.try_parse('[15/Jan/2024:10:30:04 -0500] "POST /api HTTP/1.1" 201 0')
        assert result is not None
        assert result.timestamp is not None

    def test_non_apache_returns_none(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:00Z some line")
        assert result is None

    def test_no_component(self) -> None:
        result = self.parser.try_parse('[15/Jan/2024:10:30:04 +0000] "GET / HTTP/1.1" 200 0')
        assert result is not None
        assert result.component is None


class TestApacheParserParseLine:
    def setup_method(self) -> None:
        self.parser = ApacheParser()

    def test_parse_line_apache(self) -> None:
        line = self.parser.parse_line(1, '[15/Jan/2024:10:30:04 +0000] "GET / HTTP/1.1" 200 0')
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.log_level == LogLevel.INFO

    def test_parse_line_non_apache_fallback(self) -> None:
        line = self.parser.parse_line(2, "not apache")
        assert line.timestamp is None
