"""Inspect command - view and filter log lines in a TUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from logsift.reader import is_pipe, read_file


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
    no_tail: Annotated[bool, typer.Option("--no-tail", help="Disable automatic tailing")] = False,
) -> None:
    """View and filter log lines in a terminal UI."""
    if file is not None and not file.is_file():
        typer.echo(f"Error: {file} is not a file")
        raise typer.Exit(1)

    pipe = is_pipe() if file is None else False
    tail = not no_tail
    pipe_fd: int | None = None

    if file is not None:
        lines = [] if tail else read_file(file)
        source = str(file)
    elif pipe:
        pipe_fd = _setup_pipe_input()
        lines = []
        source = "stdin"
    else:
        typer.echo("Error: provide a file or pipe input")
        raise typer.Exit(1)

    from logsift.app import LogSiftApp

    log_app = LogSiftApp(
        lines=lines,
        source=source,
        session_name=session,
        file_path=file,
        tail=tail if file is not None else False,
        pipe_fd=pipe_fd,
    )
    log_app.run(mouse=False)
