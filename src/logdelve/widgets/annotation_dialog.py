"""Modal dialog for entering/editing a bookmark annotation."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType


class AnnotationDialog(ModalScreen[str | None]):
    """Simple dialog for entering or editing a bookmark annotation."""

    DEFAULT_CSS = """
    AnnotationDialog {
        align: center middle;
    }

    AnnotationDialog > Vertical {
        width: 70;
        height: auto;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    AnnotationDialog > Vertical > .title {
        text-style: bold;
    }

    AnnotationDialog > Vertical > Input {
        width: 100%;
        margin-top: 1;
    }

    AnnotationDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, existing_text: str = "") -> None:
        super().__init__()
        self._existing_text = existing_text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Annotation", classes="title")
            yield Input(value=self._existing_text, placeholder="Enter annotation...", id="annotation-input")
            yield Label("Enter to save, Escape to cancel", classes="hint")

    def on_mount(self) -> None:
        self.query_one("#annotation-input", Input).focus()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        text = self.query_one("#annotation-input", Input).value
        self.dismiss(text)

    def action_cancel(self) -> None:
        self.dismiss(None)
