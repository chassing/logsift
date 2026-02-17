"""Modal dialog for entering filter patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.events import Key

from logdelve.filters import flatten_json
from logdelve.models import FilterRule, FilterType


class FilterDialog(ModalScreen[FilterRule | None]):
    """Modal dialog for entering a filter pattern.

    Supports text patterns, key=value syntax for JSON key filters, and regex.
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

    FilterDialog > Vertical > Horizontal {
        height: auto;
        margin-top: 1;
    }

    FilterDialog > Vertical > Horizontal > Checkbox {
        margin-right: 3;
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
            with Horizontal():
                yield Checkbox("Case sensitive", id="case-sensitive")
                yield Checkbox("Regex", id="regex")
            yield Label("Enter to apply, Space to toggle options, Escape to cancel", classes="hint")

    def on_mount(self) -> None:
        try:
            ol = self.query_one("#json-keys", OptionList)
            if ol.option_count > 0:
                ol.highlighted = 0
        except NoMatches:
            pass

    def on_key(self, event: Key) -> None:
        """Intercept Enter on checkboxes to submit the filter instead of toggling."""
        if event.key == "enter" and isinstance(self.focused, Checkbox):
            event.prevent_default()
            event.stop()
            self._submit_filter()

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

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._submit_filter()

    def _submit_filter(self) -> None:
        """Submit the filter with current input and options."""
        pattern = self.query_one("#filter-input", Input).value.strip()
        if not pattern:
            self.dismiss(None)
            return

        is_regex = self.query_one("#regex", Checkbox).value
        case_sensitive = self.query_one("#case-sensitive", Checkbox).value

        # key=value -> JSON key filter (only when not regex)
        if not is_regex and "=" in pattern:
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

        # Text or regex filter
        self.dismiss(
            FilterRule(
                filter_type=self._filter_type,
                pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
