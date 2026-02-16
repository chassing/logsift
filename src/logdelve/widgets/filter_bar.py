"""Compact filter status display bar."""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from logdelve.models import FilterRule


class FilterBar(Widget):
    """Compact bar showing filter count summary."""

    DEFAULT_CSS = """
    FilterBar {
        height: 1;
        dock: top;
        background: $surface-darken-1;
        display: none;
        padding: 0 1;
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

        total = len(self.filters)
        active = sum(1 for r in self.filters if r.enabled)
        includes = sum(1 for r in self.filters if r.enabled and r.filter_type.value == "include")
        excludes = sum(1 for r in self.filters if r.enabled and r.filter_type.value == "exclude")

        text = Text()
        text.append(f" {total} filters", style="bold")
        if active < total:
            text.append(f" ({active} active)", style="dim")

        parts = []
        if includes:
            parts.append(f"+{includes}")
        if excludes:
            parts.append(f"-{excludes}")
        if parts:
            text.append(f"  [{', '.join(parts)}]", style="dim")

        text.append("  |  ", style="dim")
        text.append("m", style="bold")
        text.append(" Manage filters", style="dim")

        return text
