"""Inspect command - view and filter log lines in a TUI."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - typer needs this at runtime for argument parsing
from typing import TYPE_CHECKING, Annotated

import typer

from logdelve.parsers import ParserName, detect_parser, get_parser
from logdelve.reader import is_pipe, read_file, read_file_initial

if TYPE_CHECKING:
    from logdelve.models import LogLine
    from logdelve.parsers import LogParser

_CHUNKED_THRESHOLD = 1_000_000  # 1MB
_TIMESTAMP_MIN = datetime.min.replace(tzinfo=UTC)


def _resolve_parser(parser_name: ParserName, file: Path | None) -> LogParser:
    """Resolve the parser to use. Auto-detect if 'auto' and file is given."""
    if parser_name != ParserName.AUTO:
        return get_parser(parser_name)

    # For auto mode with a file, sample first lines for detection
    if file is not None:
        with file.open() as f:
            sample = [f.readline().rstrip("\n") for _ in range(20)]
        return detect_parser(sample)

    # stdin/pipe: can't sample ahead, use AutoParser (per-line detection)
    return get_parser(ParserName.AUTO)


def _setup_pipe_input() -> int:
    """Save stdin pipe fd, then redirect fd 0 to /dev/tty for Textual keyboard.

    Returns the saved pipe fd for reading data.
    """
    # Save the pipe fd
    pipe_fd = os.dup(sys.stdin.fileno())
    # Redirect fd 0 to /dev/tty for Textual keyboard input
    tty_fd = os.open("/dev/tty", os.O_RDONLY)
    os.dup2(tty_fd, sys.stdin.fileno())
    os.close(tty_fd)
    sys.stdin = os.fdopen(0)
    return pipe_fd


def _tag_component(lines: list[LogLine], filename: str) -> None:
    """Set component to filename stem for lines without a parser-detected component."""
    for line in lines:
        if line.component is None:
            line.component = filename


def _sort_and_renumber(lines: list[LogLine]) -> None:
    """Sort lines by timestamp and assign merged line numbers."""
    lines.sort(key=lambda line: line.timestamp or _TIMESTAMP_MIN)
    for i, line in enumerate(lines):
        line.source_line_number = line.line_number
        line.line_number = i + 1


def _run_multi_file(
    files: list[Path],
    parser: ParserName,
    session: str | None,
    baseline: Path | None,
    start: str | None = None,
    end: str | None = None,
) -> None:
    """Handle multi-file mode: read, tag, merge, and launch TUI."""
    all_lines: list[LogLine] = []
    file_parsers: list[LogParser] = []
    file_initial_counts: list[int] = []

    for f in files:
        file_parser = _resolve_parser(parser, f)
        file_parsers.append(file_parser)
        file_lines = read_file_initial(f, parser=file_parser)
        _tag_component(file_lines, f.stem)
        file_initial_counts.append(len(file_lines))
        all_lines.extend(file_lines)

    _sort_and_renumber(all_lines)

    from logdelve.app import LogDelveApp  # noqa: PLC0415

    log_app = LogDelveApp(
        lines=all_lines,
        source=", ".join(f.name for f in files),
        session_name=session,
        baseline_path=baseline,
        file_paths=files,
        file_parsers=file_parsers,
        file_initial_counts=file_initial_counts,
        start_time=start,
        end_time=end,
    )
    log_app.run(mouse=False)


def inspect(  # noqa: C901
    files: Annotated[list[Path] | None, typer.Argument(help="Log file(s) to view")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="Load a saved filter session")] = None,
    tail: Annotated[bool, typer.Option("--tail", "-t", help="Tail the log file (follow new lines)")] = False,  # noqa: FBT002
    baseline: Annotated[
        Path | None, typer.Option("--baseline", "-b", help="Baseline log file for anomaly detection")
    ] = None,
    parser: Annotated[
        ParserName, typer.Option("--parser", "-p", help="Log format parser (default: auto-detect)")
    ] = ParserName.AUTO,
    start: Annotated[str | None, typer.Option("--start", "-S", help="Start of time range filter (inclusive)")] = None,
    end: Annotated[str | None, typer.Option("--end", "-E", help="End of time range filter (exclusive)")] = None,
) -> None:
    """View and filter log lines in a terminal UI."""
    if files:
        for f in files:
            if not f.is_file():
                typer.echo(f"Error: {f} is not a file")
                raise typer.Exit(1)

    if baseline is not None and not baseline.is_file():
        typer.echo(f"Error: baseline file {baseline} not found")
        raise typer.Exit(1)

    if tail and files and len(files) > 1:
        typer.echo("Error: --tail is only supported with a single file")
        raise typer.Exit(1)

    # Multi-file mode
    if files and len(files) > 1:
        _run_multi_file(files, parser, session, baseline, start=start, end=end)
        return

    # Single-file or pipe mode
    pipe = is_pipe() if not files else False
    pipe_fd: int | None = None
    file_size: int | None = None
    file = files[0] if files else None

    if file is not None:
        log_parser = _resolve_parser(parser, file)
        file_size = file.stat().st_size
        if tail:
            lines: list[LogLine] = []
        elif file_size > _CHUNKED_THRESHOLD:
            lines = read_file_initial(file, parser=log_parser)
        else:
            lines = read_file(file, parser=log_parser)
            file_size = None  # signal: no background loading needed
        source = str(file)
    elif pipe:
        log_parser = _resolve_parser(parser, None)
        pipe_fd = _setup_pipe_input()
        lines = []
        source = "stdin"
    else:
        typer.echo("Error: provide a file or pipe input")
        raise typer.Exit(1)

    from logdelve.app import LogDelveApp  # noqa: PLC0415

    log_app = LogDelveApp(
        lines=lines,
        source=source,
        session_name=session,
        file_path=file,
        tail=tail if file is not None else False,
        pipe_fd=pipe_fd,
        baseline_path=baseline,
        parser=log_parser,
        file_size=file_size,
        start_time=start,
        end_time=end,
    )
    log_app.run(mouse=False)
