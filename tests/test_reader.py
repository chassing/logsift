"""Tests for file reading."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from logdelve.models import ContentType
from logdelve.reader import is_pipe, read_file, read_stdin


class TestReadFile:
    def test_read_sample_file(self, sample_log_file: Path) -> None:
        lines = read_file(sample_log_file)
        assert len(lines) == 10  # 10 lines in sample including empty

    def test_line_numbers_sequential(self, sample_log_file: Path) -> None:
        lines = read_file(sample_log_file)
        for i, line in enumerate(lines, start=1):
            assert line.line_number == i

    def test_json_lines_detected(self, sample_log_file: Path) -> None:
        lines = read_file(sample_log_file)
        json_lines = [line for line in lines if line.content_type == ContentType.JSON]
        assert len(json_lines) >= 3  # at least 3 JSON lines in sample

    def test_empty_file(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.log"
        empty_file.write_text("")
        lines = read_file(empty_file)
        assert len(lines) == 0

    def test_single_line(self, tmp_path: Path) -> None:
        log_file = tmp_path / "single.log"
        log_file.write_text("2024-01-15T10:30:00Z hello world\n")
        lines = read_file(log_file)
        assert len(lines) == 1
        assert lines[0].content == "hello world"
        assert lines[0].timestamp is not None


class TestReadStdin:
    def test_read_stdin(self) -> None:
        fake_input = '2024-01-15T10:30:00Z {"key": "value"}\nplain text line\n'
        with patch("logdelve.reader.sys.stdin", StringIO(fake_input)):
            lines = read_stdin()
        assert len(lines) == 2
        assert lines[0].content_type == ContentType.JSON
        assert lines[1].content_type == ContentType.TEXT

    def test_read_stdin_empty(self) -> None:
        with patch("logdelve.reader.sys.stdin", StringIO("")):
            lines = read_stdin()
        assert len(lines) == 0


class TestIsPipe:
    def test_is_pipe_true(self) -> None:
        with patch("logdelve.reader.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert is_pipe() is True

    def test_is_pipe_false(self) -> None:
        with patch("logdelve.reader.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert is_pipe() is False
