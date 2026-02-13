"""Active filter display bar."""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from logsift.models import FilterRule, FilterType


class FilterBar(Widget):
    """Horizontal bar showing active filters."""

    DEFAULT_CSS = """
    FilterBar {
        height: 1;
        dock: top;
        background: $surface-darken-1;
        display: none;
    }

    FilterBar.has-filters {
        display: block;
    }
    """

    filters: reactive[list[FilterRule]] = reactive(list, always_update=True)

    def update_filters(self, rules: list[FilterRule]) -> None:
        """Update the displayed filters."""
        self.filters = list(rules)
        if rules:
            self.add_class("has-filters")
        else:
            self.remove_class("has-filters")

    def render(self) -> Text:
        if not self.filters:
            return Text()

        text = Text()
        for i, rule in enumerate(self.filters):
            prefix = "+" if rule.filter_type == FilterType.INCLUDE else "-"
            style = "green" if rule.filter_type == FilterType.INCLUDE else "red"
            if not rule.enabled:
                style = "dim"

            if i > 0:
                text.append(" ")
            text.append(f"[{i + 1}] ", style="dim")
            text.append(f"{prefix}{rule.pattern}", style=style)

        return text
