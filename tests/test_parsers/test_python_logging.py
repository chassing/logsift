"""Tests for Python logging parser."""

from __future__ import annotations

from logdelve.models import LogLevel
from logdelve.parsers.python_logging import PythonLoggingParser


class TestPythonLoggingParserTryParse:
    def setup_method(self) -> None:
        self.parser = PythonLoggingParser()

    def test_basic_python_log(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00,123 - myapp.module - ERROR - Something went wrong")
        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2024
        assert result.timestamp.microsecond == 123000
        assert result.component == "myapp.module"
        assert result.log_level == LogLevel.ERROR
        assert result.content == "Something went wrong"

    def test_info_level(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00,000 - root - INFO - Server started")
        assert result is not None
        assert result.log_level == LogLevel.INFO
        assert result.component == "root"

    def test_warning_level(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00,500 - app - WARNING - Deprecated")
        assert result is not None
        assert result.log_level == LogLevel.WARN

    def test_debug_level(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00,999 - debug.module - DEBUG - trace info")
        assert result is not None
        assert result.log_level == LogLevel.DEBUG

    def test_without_separators(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00,123 myapp INFO Server started")
        assert result is not None
        assert result.component == "myapp"
        assert result.log_level == LogLevel.INFO

    def test_non_python_returns_none(self) -> None:
        result = self.parser.try_parse("Jan 15 10:30:03 syslog line")
        assert result is None

    def test_iso_without_comma_returns_none(self) -> None:
        result = self.parser.try_parse("2024-01-15 10:30:00.123 some text")
        assert result is None


class TestPythonLoggingParserParseLine:
    def setup_method(self) -> None:
        self.parser = PythonLoggingParser()

    def test_parse_line(self) -> None:
        line = self.parser.parse_line(1, "2024-01-15 10:30:00,123 - app - INFO - ok")
        assert line.line_number == 1
        assert line.timestamp is not None
        assert line.log_level == LogLevel.INFO
        assert line.component == "app"

    def test_parse_line_non_python_fallback(self) -> None:
        line = self.parser.parse_line(2, "not python log")
        assert line.timestamp is None
