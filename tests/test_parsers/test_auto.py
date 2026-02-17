"""Tests for AutoParser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.auto import AutoParser


class TestAutoParserTryParse:
    def setup_method(self) -> None:
        self.parser = AutoParser()

    def test_iso_line(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:00Z some message")
        assert result is not None
        assert result.timestamp is not None
        assert result.content == "some message"

    def test_syslog_line(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 myhost syslogd: restart")
        assert result is not None
        assert result.timestamp is not None
        assert result.component == "syslogd"

    def test_apache_line(self) -> None:
        result = self.parser.try_parse('[15/Jan/2024:10:30:04 +0000] "GET / HTTP/1.1" 200 0')
        assert result is not None
        assert result.timestamp is not None

    def test_docker_compose_line(self) -> None:
        result = self.parser.try_parse("web  | 2024-01-15T10:30:00Z hello")
        assert result is not None
        assert result.component == "web"
        assert result.timestamp is not None

    def test_kubernetes_bracket_line(self) -> None:
        result = self.parser.try_parse("[my-pod] 2024-01-15T10:30:00Z msg")
        assert result is not None
        assert result.component == "my-pod"

    def test_plain_text_returns_none(self) -> None:
        result = self.parser.try_parse("just text")
        assert result is None

    def test_empty_returns_none(self) -> None:
        result = self.parser.try_parse("")
        assert result is None

    def test_json_with_level(self) -> None:
        result = self.parser.try_parse('2024-01-15T10:30:00Z {"level": "error", "msg": "fail"}')
        assert result is not None
        assert result.log_level == LogLevel.ERROR
        assert result.content_type == ContentType.JSON


class TestAutoParserParseLine:
    def setup_method(self) -> None:
        self.parser = AutoParser()

    def test_fallback_for_plain_text(self) -> None:
        line = self.parser.parse_line(1, "just text")
        assert line.line_number == 1
        assert line.timestamp is None
        assert line.content == "just text"
        assert line.log_level is None

    def test_default_info_for_timestamped(self) -> None:
        line = self.parser.parse_line(1, "2024-01-15T10:30:00Z no level here")
        assert line.log_level == LogLevel.INFO
