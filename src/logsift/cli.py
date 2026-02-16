"""CLI entry point for logsift."""

from __future__ import annotations

import typer

from logsift.commands.cloudwatch import cw_app
from logsift.commands.inspect import inspect

app = typer.Typer(add_completion=False)
app.command()(inspect)
app.add_typer(cw_app, name="cloudwatch")


def main() -> None:
    """Entry point for the CLI."""
    app()
