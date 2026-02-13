"""Log file reading."""

from __future__ import annotations

import sys
from pathlib import Path

from logsift.models import LogLine
from logsift.parser import parse_line


def read_file(path: Path) -> list[LogLine]:
    """Read all log lines from a file."""
    lines: list[LogLine] = []
    with path.open() as f:
        for i, raw_line in enumerate(f, start=1):
            lines.append(parse_line(i, raw_line.rstrip("\n")))
    return lines


def is_pipe() -> bool:
    """Check if stdin is a pipe (not a terminal)."""
    return not sys.stdin.isatty()


def read_stdin() -> list[LogLine]:
    """Read all log lines from stdin."""
    lines: list[LogLine] = []
    for i, raw_line in enumerate(sys.stdin, start=1):
        lines.append(parse_line(i, raw_line.rstrip("\n")))
    return lines
