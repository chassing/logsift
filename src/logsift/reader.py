"""Log file reading (sync and async with tailing)."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from logsift.models import LogLine
from logsift.parser import parse_line


def read_file(path: Path) -> list[LogLine]:
    """Read all log lines from a file (synchronous)."""
    lines: list[LogLine] = []
    with path.open() as f:
        for i, raw_line in enumerate(f, start=1):
            lines.append(parse_line(i, raw_line.rstrip("\n")))
    return lines


def is_pipe() -> bool:
    """Check if stdin is a pipe (not a terminal)."""
    return not sys.stdin.isatty()


def read_stdin() -> list[LogLine]:
    """Read all log lines from stdin (synchronous)."""
    lines: list[LogLine] = []
    for i, raw_line in enumerate(sys.stdin, start=1):
        lines.append(parse_line(i, raw_line.rstrip("\n")))
    return lines


async def read_file_async(path: Path, tail: bool = False) -> AsyncIterator[LogLine]:
    """Read log lines from a file asynchronously, optionally tailing."""
    line_number = 0
    async with aiofiles.open(path) as f:
        async for raw_line in f:
            line_number += 1
            yield parse_line(line_number, raw_line.rstrip("\n"))

        if not tail:
            return

        # Tail mode: poll for new content
        last_size = path.stat().st_size
        while True:
            line = await f.readline()
            if line:
                line_number += 1
                yield parse_line(line_number, line.rstrip("\n"))
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


async def read_stdin_async() -> AsyncIterator[LogLine]:
    """Read log lines from stdin asynchronously."""
    line_number = 0
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break
        line_number += 1
        yield parse_line(line_number, line_bytes.decode().rstrip("\n"))
