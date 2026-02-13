"""Tests for file reading."""

from __future__ import annotations

from pathlib import Path

from logsift.models import ContentType
from logsift.reader import read_file


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
