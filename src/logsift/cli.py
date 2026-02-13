"""CLI entry point for logsift."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(add_completion=False)


@app.command()
def run(
    file: Annotated[Path | None, typer.Argument(help="Log file to view")] = None,
) -> None:
    """View and filter log lines in a terminal UI."""
    if file is not None and not file.is_file():
        typer.echo(f"Error: {file} is not a file")
        raise typer.Exit(1)

    from logsift.app import LogSiftApp

    log_app = LogSiftApp(file=file)
    log_app.run()


def main() -> None:
    """Entry point for the CLI."""
    app()
