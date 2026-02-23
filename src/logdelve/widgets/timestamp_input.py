"""Reusable timestamp input widget with validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Vertical
from textual.widgets import Input, Label

from logdelve.utils import parse_time

if TYPE_CHECKING:
    from datetime import datetime

    from textual.app import ComposeResult


class TimestampInput(Vertical):
    """Composite widget: timestamp Input + error Label.

    Parses timestamps via `utils.parse_time()` which supports ISO 8601,
    relative shorthand (5m, 1h), and natural language (yesterday, friday).
    Reusable in search dialog and time range filter dialog.
    """

    DEFAULT_CSS: ClassVar[str] = """
    TimestampInput {
        height: auto;
    }

    TimestampInput > Input {
        width: 100%;
    }

    TimestampInput > .error {
        color: $error;
        height: auto;
        display: none;
    }

    TimestampInput > .error.visible {
        display: block;
    }
    """

    def __init__(
        self,
        placeholder: str = "14:30, 2024-01-15T10:30:00Z, 5m, yesterday...",
        reference_date: datetime | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(**kwargs)
        self._placeholder = placeholder
        self._reference_date = reference_date

    def compose(self) -> ComposeResult:
        """Compose the input and error label."""
        yield Input(placeholder=self._placeholder, id="ts-input")
        yield Label("", classes="error", id="ts-error")

    @property
    def value(self) -> str:
        """Get the raw input value."""
        return self.query_one("#ts-input", Input).value.strip()

    def focus_input(self) -> None:
        """Focus the text input."""
        self.query_one("#ts-input", Input).focus()

    def parse(self) -> datetime | None:
        """Parse the input value as a timestamp.

        Returns the parsed datetime on success, or None on failure (shows error inline).
        """
        raw = self.value
        if not raw:
            return None

        try:
            result = parse_time(raw, reference_date=self._reference_date)
        except ValueError as e:
            error_label = self.query_one("#ts-error", Label)
            error_label.update(str(e))
            error_label.add_class("visible")
            return None

        # Clear any previous error
        error_label = self.query_one("#ts-error", Label)
        error_label.remove_class("visible")
        return result

    def clear_error(self) -> None:
        """Clear the error display."""
        self.query_one("#ts-error", Label).remove_class("visible")
