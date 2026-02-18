"""Tests for file reading."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from logdelve.models import ContentType
from logdelve.reader import is_pipe, read_file, read_file_initial, read_file_remaining_async, read_stdin


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


class TestReadFileInitial:
    def test_read_initial_limits_lines(self, tmp_path: Path) -> None:
        log_file = tmp_path / "large.log"
        log_file.write_text("\n".join(f"line {i}" for i in range(100)) + "\n")
        lines = read_file_initial(log_file, count=10)
        assert len(lines) == 10
        assert lines[0].raw == "line 0"
        assert lines[9].raw == "line 9"

    def test_read_initial_small_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "small.log"
        log_file.write_text("line 1\nline 2\n")
        lines = read_file_initial(log_file, count=100)
        assert len(lines) == 2

    def test_read_initial_empty_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "empty.log"
        log_file.write_text("")
        lines = read_file_initial(log_file, count=10)
        assert len(lines) == 0


class TestReadFileRemainingAsync:
    @pytest.mark.asyncio
    async def test_remaining_skips_initial(self, tmp_path: Path) -> None:
        log_file = tmp_path / "large.log"
        log_file.write_text("\n".join(f"line {i}" for i in range(50)) + "\n")
        chunks = [chunk async for chunk in read_file_remaining_async(log_file, skip=10, chunk_size=20)]
        total = sum(len(c) for c in chunks)
        assert total == 40  # 50 - 10 skipped
        # First line in first chunk should be line 10 (line_number=11)
        assert chunks[0][0].raw == "line 10"
        assert chunks[0][0].line_number == 11

    @pytest.mark.asyncio
    async def test_remaining_yields_chunks(self, tmp_path: Path) -> None:
        log_file = tmp_path / "large.log"
        log_file.write_text("\n".join(f"line {i}" for i in range(100)) + "\n")
        chunks = [chunk async for chunk in read_file_remaining_async(log_file, skip=0, chunk_size=30)]
        assert len(chunks) == 4  # 30 + 30 + 30 + 10
        assert len(chunks[0]) == 30
        assert len(chunks[-1]) == 10

    @pytest.mark.asyncio
    async def test_remaining_nothing_to_read(self, tmp_path: Path) -> None:
        log_file = tmp_path / "small.log"
        log_file.write_text("line 1\nline 2\n")
        chunks = [chunk async for chunk in read_file_remaining_async(log_file, skip=10, chunk_size=100)]
        assert len(chunks) == 0


class TestIsPipe:
    def test_is_pipe_true(self) -> None:
        with patch("logdelve.reader.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert is_pipe() is True

    def test_is_pipe_false(self) -> None:
        with patch("logdelve.reader.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert is_pipe() is False
