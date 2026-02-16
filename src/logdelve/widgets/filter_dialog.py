"""Modal dialog for entering filter patterns."""

from __future__ import annotations

from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from logdelve.filters import flatten_json
from logdelve.models import FilterRule, FilterType


class FilterDialog(ModalScreen[FilterRule | None]):
    """Modal dialog for entering a filter pattern.

    Supports text patterns and key=value syntax for JSON key filters.
    When json_data is provided, shows clickable key-value suggestions.
    """

    DEFAULT_CSS = """
    FilterDialog {
        align: center middle;
    }

    FilterDialog > Vertical {
        width: 90%;
        height: auto;
        max-height: 25;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    FilterDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    FilterDialog > Vertical > OptionList {
        height: auto;
        max-height: 12;
    }

    FilterDialog > Vertical > Input {
        width: 100%;
        margin-top: 1;
    }

    FilterDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, filter_type: FilterType, json_data: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._filter_type = filter_type
        self._json_data = json_data
        self._pairs: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        label = "Filter in (show matching)" if self._filter_type == FilterType.INCLUDE else "Filter out (hide matching)"
        with Vertical():
            yield Label(label, classes="title")

            if self._json_data:
                self._pairs = flatten_json(self._json_data)
                ol = OptionList(id="json-keys")
                for key, value in self._pairs:
                    ol.add_option(Option(f"{key} = {value}"))
                yield ol

            yield Input(
                placeholder="text pattern or key=value...",
                id="filter-input",
            )
            yield Label("Enter to apply, Escape to cancel", classes="hint")

    def on_mount(self) -> None:
        try:
            ol = self.query_one("#json-keys", OptionList)
            if ol.option_count > 0:
                ol.highlighted = 0
        except Exception:
            pass

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_index < len(self._pairs):
            key, value = self._pairs[event.option_index]
            rule = FilterRule(
                filter_type=self._filter_type,
                pattern=f"{key}={value}",
                is_json_key=True,
                json_key=key,
                json_value=value,
            )
            self.dismiss(rule)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        pattern = event.value.strip()
        if not pattern:
            self.dismiss(None)
            return

        # key=value -> JSON key filter
        if "=" in pattern:
            key, _, value = pattern.partition("=")
            key = key.strip()
            value = value.strip()
            if key:
                self.dismiss(
                    FilterRule(
                        filter_type=self._filter_type,
                        pattern=pattern,
                        is_json_key=True,
                        json_key=key,
                        json_value=value,
                    )
                )
                return

        # Plain text filter
        self.dismiss(FilterRule(filter_type=self._filter_type, pattern=pattern))

    def action_cancel(self) -> None:
        self.dismiss(None)
