"""Modal dialog for entering filter patterns."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label

from logsift.models import FilterRule, FilterType


class FilterDialog(ModalScreen[FilterRule | None]):
    """Modal dialog for entering a filter pattern."""

    DEFAULT_CSS = """
    FilterDialog {
        align: center middle;
    }

    FilterDialog > Vertical {
        width: 70;
        height: auto;
        max-height: 12;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    FilterDialog > Vertical > Label {
        margin-bottom: 1;
        text-style: bold;
    }

    FilterDialog > Vertical > Input {
        width: 100%;
    }

    FilterDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, filter_type: FilterType) -> None:
        super().__init__()
        self._filter_type = filter_type

    def compose(self) -> ComposeResult:
        label = "Filter in (show matching)" if self._filter_type == FilterType.INCLUDE else "Filter out (hide matching)"
        with Vertical():
            yield Label(label)
            yield Input(placeholder="Enter pattern...", id="filter-input")
            yield Label("Enter to apply, Escape to cancel", classes="hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        pattern = event.value.strip()
        if pattern:
            self.dismiss(FilterRule(filter_type=self._filter_type, pattern=pattern))
        else:
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
