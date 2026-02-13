"""Textual application for logsift."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType

from logsift.models import LogLine
from logsift.widgets.log_view import LogView


class LogSiftApp(App[None]):
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, lines: list[LogLine] | None = None) -> None:
        super().__init__()
        self._lines = lines or []

    def compose(self) -> ComposeResult:
        yield LogView(id="log-view")

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        if self._lines:
            log_view.set_lines(self._lines)
