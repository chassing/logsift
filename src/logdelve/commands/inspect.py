"""Inspect command - view and filter log lines in a TUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path  # noqa: TC003 - typer needs this at runtime for argument parsing
from typing import TYPE_CHECKING, Annotated

import typer

from logdelve.parsers import ParserName, detect_parser, get_parser
from logdelve.reader import is_pipe, read_file, read_file_initial

if TYPE_CHECKING:
    from logdelve.parsers import LogParser

_CHUNKED_THRESHOLD = 1_000_000  # 1MB


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


def inspect(
    file: Annotated[Path | None, typer.Argument(help="Log file to view")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="Load a saved filter session")] = None,
    tail: Annotated[bool, typer.Option("--tail", "-t", help="Tail the log file (follow new lines)")] = False,  # noqa: FBT002
    baseline: Annotated[
        Path | None, typer.Option("--baseline", "-b", help="Baseline log file for anomaly detection")
    ] = None,
    parser: Annotated[
        ParserName, typer.Option("--parser", "-p", help="Log format parser (default: auto-detect)")
    ] = ParserName.AUTO,
) -> None:
    """View and filter log lines in a terminal UI."""
    if file is not None and not file.is_file():
        typer.echo(f"Error: {file} is not a file")
        raise typer.Exit(1)

    if baseline is not None and not baseline.is_file():
        typer.echo(f"Error: baseline file {baseline} not found")
        raise typer.Exit(1)

    log_parser = _resolve_parser(parser, file)
    pipe = is_pipe() if file is None else False
    pipe_fd: int | None = None

    file_size: int | None = None
    if file is not None:
        file_size = file.stat().st_size
        if tail:
            lines = []
        elif file_size > _CHUNKED_THRESHOLD:
            lines = read_file_initial(file, parser=log_parser)
        else:
            lines = read_file(file, parser=log_parser)
            file_size = None  # signal: no background loading needed
        source = str(file)
    elif pipe:
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
    )
    log_app.run(mouse=False)
