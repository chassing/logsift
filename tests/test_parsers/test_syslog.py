"""Tests for syslog parser."""

from __future__ import annotations

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.syslog import SyslogParser


class TestSyslogParserTryParse:
    def setup_method(self) -> None:
        self.parser = SyslogParser()

    def test_basic_syslog(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 myhost syslogd: restart")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.month == 1
        assert result.timestamp.day == 15
        assert result.timestamp.hour == 10
        assert result.timestamp.minute == 30
        assert result.timestamp.second == 3
        assert result.component == "syslogd"
        assert "restart" in result.content

    def test_single_digit_day(self) -> None:
        result = self.parser.try_parse("Jan  5 10:30:03 myhost syslogd: restart")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.day == 5

    def test_non_syslog_returns_none(self) -> None:
        result = self.parser.try_parse("2024-01-15T10:30:00Z some ISO line")
        assert result is None

    def test_program_with_pid(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 server01 nginx[1234]: GET /index.html")
        assert result is not None
        assert result.component == "nginx"
        assert "GET /index.html" in result.content

    def test_program_without_pid(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 server01 kernel: something happened")
        assert result is not None
        assert result.component == "kernel"

    def test_systemd_with_pid(self) -> None:
        result = self.parser.try_parse("Feb 17 09:58:07 prod-ci-int-bastion systemd[3877079]: Reached target Sockets.")
        assert result is not None
        assert result.component == "systemd"
        assert result.content == "Reached target Sockets."

    def test_no_hostname_pattern(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 123invalid")
        assert result is not None
        assert result.component is None

    def test_json_content_after_syslog(self) -> None:
        result = self.parser.try_parse('Jan 15 10:30:03 myhost app: {"level": "error", "msg": "fail"}')
        assert result is not None
        assert result.content_type == ContentType.JSON
        assert result.log_level == LogLevel.ERROR

    def test_error_heuristic(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 myhost kernel: connection refused")
        assert result is not None
        assert result.log_level == LogLevel.ERROR


class TestSyslogParserParseLine:
    def setup_method(self) -> None:
        self.parser = SyslogParser()

    def test_parse_line_syslog(self) -> None:
        line = self.parser.parse_line(1, "Jan 15 10:30:03 myhost syslogd: restart")
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.component == "syslogd"
        assert line.log_level == LogLevel.INFO

    def test_parse_line_non_syslog_fallback(self) -> None:
        line = self.parser.parse_line(2, "just plain text")
        assert line.line_number == 2
        assert line.timestamp is None
        assert line.content == "just plain text"
