"""Tests for journalctl parser."""

from __future__ import annotations

import json

from logdelve.models import ContentType, LogLevel
from logdelve.parsers.journalctl import JournalctlParser


class TestJournalctlParserTryParse:
    def setup_method(self) -> None:
        self.parser = JournalctlParser()

    def test_basic_journalctl(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "Service started",
            "SYSLOG_IDENTIFIER": "systemd",
            "PRIORITY": "6",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.timestamp is not None
        assert result.content == "Service started"
        assert result.component == "systemd"
        assert result.log_level == LogLevel.INFO

    def test_priority_error(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "Something failed",
            "PRIORITY": "3",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.log_level == LogLevel.ERROR

    def test_priority_warning(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "Something slow",
            "PRIORITY": "4",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.log_level == LogLevel.WARN

    def test_priority_critical(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "System crash",
            "PRIORITY": "2",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.log_level == LogLevel.FATAL

    def test_comm_as_component(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "test",
            "_COMM": "nginx",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.component == "nginx"

    def test_syslog_identifier_priority(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "test",
            "SYSLOG_IDENTIFIER": "sshd",
            "_COMM": "sshd-child",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.component == "sshd"

    def test_no_realtime_timestamp_returns_none(self) -> None:
        data = {"MESSAGE": "no timestamp", "PRIORITY": "6"}
        result = self.parser.try_parse(json.dumps(data))
        assert result is None

    def test_non_json_returns_none(self) -> None:
        result = self.parser.try_parse("not json at all")
        assert result is None

    def test_regular_json_without_systemd_fields(self) -> None:
        result = self.parser.try_parse('{"level": "info", "msg": "hello"}')
        assert result is None

    def test_content_type_is_json(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "test",
        }
        result = self.parser.try_parse(json.dumps(data))
        assert result is not None
        assert result.content_type == ContentType.JSON
        assert result.parsed_json is not None


class TestJournalctlParserParseLine:
    def setup_method(self) -> None:
        self.parser = JournalctlParser()

    def test_parse_line_journalctl(self) -> None:
        data = {
            "__REALTIME_TIMESTAMP": "1705312200000000",
            "MESSAGE": "test",
            "PRIORITY": "6",
        }
        line = self.parser.parse_line(1, json.dumps(data))
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.log_level == LogLevel.INFO

    def test_parse_line_non_journalctl_fallback(self) -> None:
        line = self.parser.parse_line(2, "plain text")
        assert line.timestamp is None
