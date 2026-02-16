"""CLI entry point for logdelve."""

from __future__ import annotations

import typer

from logdelve.commands.cloudwatch import cw_app
from logdelve.commands.inspect import inspect

app = typer.Typer(add_completion=False)
app.command()(inspect)
app.add_typer(cw_app, name="cloudwatch")


def main() -> None:
    """Entry point for the CLI."""
    app()
