"""Modal dialog for search with options."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label

from logdelve.models import SearchDirection, SearchQuery


class SearchDialog(ModalScreen[SearchQuery | None]):
    """Modal dialog for entering a search pattern with case/regex options."""

    DEFAULT_CSS = """
    SearchDialog {
        align: center middle;
    }

    SearchDialog > Vertical {
        width: 70;
        height: auto;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    SearchDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    SearchDialog > Vertical > Input {
        width: 100%;
    }

    SearchDialog > Vertical > Horizontal {
        height: auto;
        margin-top: 1;
    }

    SearchDialog > Vertical > Horizontal > Checkbox {
        margin-right: 3;
    }

    SearchDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, direction: SearchDirection) -> None:
        super().__init__()
        self._direction = direction

    def compose(self) -> ComposeResult:
        label = "🔍 Search forward (/)" if self._direction == SearchDirection.FORWARD else "🔍 Search backward (?)"
        with Vertical():
            yield Label(label, classes="title")
            yield Input(placeholder="search pattern...", id="search-input")
            with Horizontal():
                yield Checkbox("Case sensitive", id="case-sensitive")
                yield Checkbox("Regex", id="regex")
            yield Label("Enter to search, Space to toggle options, Escape to cancel", classes="hint")

    def on_key(self, event: Key) -> None:
        """Intercept Enter on checkboxes to submit the search instead of toggling."""
        if event.key == "enter" and isinstance(self.focused, Checkbox):
            event.prevent_default()
            event.stop()
            self._submit_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit_search()

    def _submit_search(self) -> None:
        """Submit the search with current input and options."""
        pattern = self.query_one("#search-input", Input).value.strip()
        if not pattern:
            self.dismiss(None)
            return

        case_sensitive = self.query_one("#case-sensitive", Checkbox).value
        is_regex = self.query_one("#regex", Checkbox).value

        self.dismiss(
            SearchQuery(
                pattern=pattern,
                case_sensitive=case_sensitive,
                is_regex=is_regex,
                direction=self._direction,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
