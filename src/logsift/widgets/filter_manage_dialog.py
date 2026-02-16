"""Modal dialog for managing active filters."""

from __future__ import annotations

from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from logsift.models import FilterRule, FilterType


class FilterManageDialog(ModalScreen[list[FilterRule] | None]):
    """Modal dialog for managing filters: toggle, reorder, delete."""

    DEFAULT_CSS = """
    FilterManageDialog {
        align: center middle;
    }

    FilterManageDialog > Vertical {
        width: 80;
        height: 80%;
        max-height: 25;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    FilterManageDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    FilterManageDialog > Vertical > OptionList {
        height: 1fr;
    }

    FilterManageDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "done", "Done"),
        Binding("space", "toggle_filter", "Toggle"),
        Binding("enter", "toggle_filter", "Toggle", show=False),
        Binding("d", "delete_filter", "Delete"),
        Binding("c", "clear_all", "Clear all"),
        Binding("k", "move_up", "Move up"),
        Binding("i", "move_down", "Move down"),
    ]

    def __init__(self, filters: list[FilterRule]) -> None:
        super().__init__()
        self._filters = [r.model_copy() for r in filters]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Manage filters", classes="title")
            yield OptionList(id="filter-list")
            yield Label("Space: toggle  d: delete  c: clear all  k/i: move  Esc: done", classes="hint")

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        ol = self.query_one("#filter-list", OptionList)
        highlighted = ol.highlighted
        ol.clear_options()
        for i, rule in enumerate(self._filters):
            ol.add_option(Option(self._format_rule(i, rule)))
        if highlighted is not None and self._filters:
            ol.highlighted = min(highlighted, len(self._filters) - 1)

    def _format_rule(self, index: int, rule: FilterRule) -> Text:
        text = Text()
        text.append(f"[{index + 1}] ", style="dim")

        status = "ON " if rule.enabled else "OFF"
        status_style = "green bold" if rule.enabled else "red"
        text.append(f"{status} ", style=status_style)

        prefix = "+" if rule.filter_type == FilterType.INCLUDE else "-"
        label = f"{rule.json_key}={rule.json_value}" if rule.is_json_key else rule.pattern
        style = "green" if rule.filter_type == FilterType.INCLUDE else "red"
        if not rule.enabled:
            style = "dim"
        text.append(f"{prefix}{label}", style=style)

        return text

    def _get_highlighted(self) -> int | None:
        ol = self.query_one("#filter-list", OptionList)
        return ol.highlighted

    def action_toggle_filter(self) -> None:
        idx = self._get_highlighted()
        if idx is not None and 0 <= idx < len(self._filters):
            self._filters[idx].enabled = not self._filters[idx].enabled
            self._rebuild_list()

    def action_delete_filter(self) -> None:
        idx = self._get_highlighted()
        if idx is not None and 0 <= idx < len(self._filters):
            self._filters.pop(idx)
            self._rebuild_list()

    def action_clear_all(self) -> None:
        if self._filters:
            self._filters.clear()
            self._rebuild_list()

    def action_move_up(self) -> None:
        idx = self._get_highlighted()
        if idx is not None and idx > 0:
            self._filters[idx], self._filters[idx - 1] = self._filters[idx - 1], self._filters[idx]
            ol = self.query_one("#filter-list", OptionList)
            self._rebuild_list()
            ol.highlighted = idx - 1

    def action_move_down(self) -> None:
        idx = self._get_highlighted()
        if idx is not None and idx < len(self._filters) - 1:
            self._filters[idx], self._filters[idx + 1] = self._filters[idx + 1], self._filters[idx]
            ol = self.query_one("#filter-list", OptionList)
            self._rebuild_list()
            ol.highlighted = idx + 1

    def action_done(self) -> None:
        self.dismiss(self._filters)
