"""Modal dialog for exporting filtered log lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select

from logdelve.export import ExportFormat

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType


@dataclass
class ExportResult:
    """Result from the export dialog."""

    path: str
    fmt: ExportFormat
    scope: str


class ExportDialog(ModalScreen[ExportResult | None]):
    """Dialog for exporting filtered log lines to a file."""

    DEFAULT_CSS = """
    ExportDialog {
        align: center middle;
    }

    ExportDialog > Vertical {
        width: 70;
        height: auto;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    ExportDialog > Vertical > .title {
        text-style: bold;
    }

    ExportDialog > Vertical > Label {
        margin-top: 1;
    }

    ExportDialog > Vertical > Select {
        width: 100%;
    }

    ExportDialog > Vertical > Input {
        width: 100%;
        margin-top: 1;
    }

    ExportDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, *, has_bookmarks: bool = False) -> None:
        super().__init__()
        self._has_bookmarks = has_bookmarks

    def compose(self) -> ComposeResult:
        ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
        default_path = f"logdelve-export-{ts}.log"

        with Vertical():
            yield Label("Export", classes="title")

            yield Label("Output file:")
            yield Input(value=default_path, placeholder="file path...", id="path-input")

            yield Label("Scope:")
            scope_options: list[tuple[str, str]] = [
                ("Visible lines (filtered)", "visible"),
                ("All lines (unfiltered)", "all"),
            ]
            if self._has_bookmarks:
                scope_options.append(("Bookmarked lines only", "bookmarked"))
            yield Select[str](
                scope_options,
                value="visible",
                id="scope-select",
            )

            yield Label("Format:")
            yield Select[str](
                [(fmt.value, fmt.value) for fmt in ExportFormat],
                value=ExportFormat.RAW.value,
                id="format-select",
            )

            yield Label("Enter to export, Escape to cancel", classes="hint")

    def on_mount(self) -> None:
        self.query_one("#path-input", Input).focus()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        path = self.query_one("#path-input", Input).value.strip()
        if not path:
            self.notify("No output path", severity="error")
            return

        fmt_value = self.query_one("#format-select", Select).value
        fmt = ExportFormat(fmt_value) if isinstance(fmt_value, str) else ExportFormat.RAW

        scope_value = self.query_one("#scope-select", Select).value
        scope = scope_value if isinstance(scope_value, str) else "visible"

        self.dismiss(ExportResult(path, fmt, scope))

    def action_cancel(self) -> None:
        self.dismiss(None)
