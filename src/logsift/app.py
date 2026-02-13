"""Textual application for logsift."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType

from logsift.reader import read_file
from logsift.widgets.log_view import LogView


class LogSiftApp(App[None]):
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, file: Path | None = None) -> None:
        super().__init__()
        self._file = file

    def compose(self) -> ComposeResult:
        yield LogView(id="log-view")

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        if self._file is not None:
            lines = read_file(self._file)
            log_view.set_lines(lines)
