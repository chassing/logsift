"""CLI entry point for logsift."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from logsift.reader import is_pipe, read_file, read_stdin

app = typer.Typer(add_completion=False)


@app.command()
def run(
    file: Annotated[Path | None, typer.Argument(help="Log file to view")] = None,
) -> None:
    """View and filter log lines in a terminal UI."""
    if file is not None and not file.is_file():
        typer.echo(f"Error: {file} is not a file")
        raise typer.Exit(1)

    if file is not None:
        lines = read_file(file)
    elif is_pipe():
        lines = read_stdin()
    else:
        typer.echo("Error: provide a file or pipe input")
        raise typer.Exit(1)

    from logsift.app import LogSiftApp

    log_app = LogSiftApp(lines=lines)
    log_app.run()


def main() -> None:
    """Entry point for the CLI."""
    app()
