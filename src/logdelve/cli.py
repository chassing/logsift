"""CLI entry point for logdelve."""

from __future__ import annotations

import typer

from logdelve.commands.cloudwatch import cw_app
from logdelve.commands.inspect import inspect

app = typer.Typer()
app.command()(inspect)
app.add_typer(cw_app, name="cloudwatch")


@app.command()
def keybindings() -> None:
    """Print default keybindings as TOML (ready to paste into config.toml)."""
    from logdelve.keybindings import generate_defaults_toml  # noqa: PLC0415

    typer.echo(generate_defaults_toml())


def main() -> None:
    """Entry point for the CLI."""
    app()
