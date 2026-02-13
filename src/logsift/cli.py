"""CLI entry point for logsift."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from logsift.reader import is_pipe, read_file

app = typer.Typer(add_completion=False)


@app.command()
def run(
    file: Annotated[Path | None, typer.Argument(help="Log file to view")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="Load a saved filter session")] = None,
    tail: Annotated[bool, typer.Option("--tail", "-t", help="Follow file for new lines")] = False,
) -> None:
    """View and filter log lines in a terminal UI."""
    if file is not None and not file.is_file():
        typer.echo(f"Error: {file} is not a file")
        raise typer.Exit(1)

    pipe = is_pipe() if file is None else False

    if file is not None:
        lines = [] if tail else read_file(file)
        source = str(file)
    elif pipe:
        lines = []  # Lines arrive via async reader
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
        tail=tail,
        pipe_input=pipe,
    )
    log_app.run(mouse=False)


def main() -> None:
    """Entry point for the CLI."""
    app()
