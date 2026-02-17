"""Log file reading (sync and async with tailing)."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from logdelve.models import LogLine
from logdelve.parsers.base import LogParser


def _default_parser() -> LogParser:
    """Get the default parser (AutoParser)."""
    from logdelve.parsers import ParserName, get_parser

    return get_parser(ParserName.AUTO)


def read_file(path: Path, parser: LogParser | None = None) -> list[LogLine]:
    """Read all log lines from a file (synchronous)."""
    p = parser or _default_parser()
    lines: list[LogLine] = []
    with path.open() as f:
        for i, raw_line in enumerate(f, start=1):
            lines.append(p.parse_line(i, raw_line.rstrip("\n")))
    return lines


def is_pipe() -> bool:
    """Check if stdin is a pipe (not a terminal)."""
    return not sys.stdin.isatty()


def read_stdin(parser: LogParser | None = None) -> list[LogLine]:
    """Read all log lines from stdin (synchronous)."""
    p = parser or _default_parser()
    lines: list[LogLine] = []
    for i, raw_line in enumerate(sys.stdin, start=1):
        lines.append(p.parse_line(i, raw_line.rstrip("\n")))
    return lines


async def read_file_async(path: Path, tail: bool = False, parser: LogParser | None = None) -> AsyncIterator[LogLine]:
    """Read log lines from a file asynchronously, optionally tailing."""
    p = parser or _default_parser()
    line_number = 0
    async with aiofiles.open(path) as f:
        async for raw_line in f:
            line_number += 1
            yield p.parse_line(line_number, raw_line.rstrip("\n"))

        if not tail:
            return

        # Tail mode: poll for new content
        last_size = path.stat().st_size
        while True:
            line = await f.readline()
            if line:
                line_number += 1
                yield p.parse_line(line_number, line.rstrip("\n"))
            else:
                # Check for file truncation (log rotation)
                try:
                    current_size = path.stat().st_size
                except OSError:
                    await asyncio.sleep(0.2)
                    continue
                if current_size < last_size:
                    # File was truncated, seek to beginning
                    await f.seek(0)
                    line_number = 0
                last_size = current_size
                await asyncio.sleep(0.1)


async def read_pipe_async(pipe_fd: int, parser: LogParser | None = None) -> AsyncIterator[LogLine]:
    """Read log lines from a pipe file descriptor asynchronously."""
    p = parser or _default_parser()
    line_number = 0
    async with aiofiles.open(pipe_fd, closefd=True) as f:
        async for raw_line in f:
            line_number += 1
            yield p.parse_line(line_number, raw_line.rstrip("\n"))
