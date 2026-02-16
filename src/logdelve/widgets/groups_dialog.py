"""Modal dialog for message group analysis."""

from __future__ import annotations

from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from logdelve.models import FilterRule, FilterType, LogLevel, LogLine
from logdelve.templates import (
    FieldGroup,
    MessageTemplate,
    build_field_groups,
    build_template_groups,
    template_to_regex,
)

_LEVEL_ORDER: dict[LogLevel | None, int] = {
    LogLevel.FATAL: 0,
    LogLevel.ERROR: 1,
    LogLevel.WARN: 2,
    LogLevel.INFO: 3,
    LogLevel.DEBUG: 4,
    LogLevel.TRACE: 5,
    None: 6,
}


class GroupsDialog(ModalScreen[FilterRule | None]):
    """Message group analysis dialog with separate mode, sort, and order controls."""

    DEFAULT_CSS = """
    GroupsDialog {
        align: center middle;
    }

    GroupsDialog > Vertical {
        width: 90%;
        height: 80%;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    GroupsDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    GroupsDialog > Vertical > OptionList {
        height: 1fr;
    }

    GroupsDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Close"),
        Binding("m", "toggle_mode", "Mode"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("r", "reverse_order", "Reverse"),
    ]

    def __init__(self, lines: list[LogLine]) -> None:
        super().__init__()
        self._lines = lines
        self._template_groups: list[MessageTemplate] = []
        self._field_groups: list[FieldGroup] = []
        self._mode = "messages"  # messages | fields
        self._sort = "count"  # count | level (messages) or count | key (fields)
        self._reverse = False  # False = default order, True = reversed

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("", id="groups-title", classes="title")
            yield OptionList(id="groups-list")
            yield Label(
                "Enter: filter  m: mode  s: sort  r: reverse  Esc: close",
                classes="hint",
            )

    def on_mount(self) -> None:
        self._template_groups = build_template_groups(self._lines)
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        ol = self.query_one("#groups-list", OptionList)
        highlighted = ol.highlighted
        ol.clear_options()
        title_label = self.query_one("#groups-title", Label)

        order_arrow = "↑" if self._reverse else "↓"
        item_count = 0

        if self._mode == "fields":
            if not self._field_groups:
                self._field_groups = build_field_groups(self._lines)
            field_items = self._sorted_field_groups()
            item_count = len(field_items)
            title_label.update(
                f"📊 {item_count} field values  |  sort: {self._sort} {order_arrow}  |  mode: fields"
            )
            for fg in field_items:
                ol.add_option(Option(self._format_field_group(fg)))
        else:
            tmpl_items = self._sorted_template_groups()
            item_count = len(tmpl_items)
            title_label.update(
                f"📊 {item_count} patterns  |  sort: {self._sort} {order_arrow}  |  mode: messages"
            )
            for group in tmpl_items:
                ol.add_option(Option(self._format_template_group(group)))

        if highlighted is not None and item_count > 0:
            ol.highlighted = min(highlighted, item_count - 1)

    def _sorted_template_groups(self) -> list[MessageTemplate]:
        groups = list(self._template_groups)
        if self._sort == "count":
            groups.sort(key=lambda g: g.count, reverse=not self._reverse)
        elif self._sort == "level":
            groups.sort(
                key=lambda g: (_LEVEL_ORDER.get(g.log_level, 6), -g.count),
                reverse=self._reverse,
            )
        return groups

    def _sorted_field_groups(self) -> list[FieldGroup]:
        groups = list(self._field_groups)
        if self._sort == "count":
            groups.sort(key=lambda g: g.count, reverse=not self._reverse)
        elif self._sort == "key":
            groups.sort(key=lambda g: (g.key, g.count), reverse=self._reverse)
        return groups

    def _format_template_group(self, group: MessageTemplate) -> Text:
        text = Text()

        if group.log_level is not None:
            badge_chars = {
                LogLevel.FATAL: "F",
                LogLevel.ERROR: "E",
                LogLevel.WARN: "W",
                LogLevel.INFO: "I",
                LogLevel.DEBUG: "D",
                LogLevel.TRACE: "T",
            }
            badge = badge_chars.get(group.log_level, "?")
            level_styles = {
                LogLevel.FATAL: "bold red",
                LogLevel.ERROR: "red",
                LogLevel.WARN: "yellow",
                LogLevel.INFO: "",
                LogLevel.DEBUG: "dim",
                LogLevel.TRACE: "dim",
            }
            style = level_styles.get(group.log_level, "")
            text.append(f" {badge} ", style=style)
        else:
            text.append(" - ")

        text.append(f"{group.count:>6}x  ", style="bold")
        text.append(group.display)

        return text

    def _format_field_group(self, fg: FieldGroup) -> Text:
        text = Text()
        text.append(f"  {fg.count:>6}x  ", style="bold")
        text.append(fg.key, style="green")
        text.append(": ")
        text.append(fg.value)
        return text

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if self._mode == "fields":
            field_items = self._sorted_field_groups()
            if 0 <= idx < len(field_items):
                fg = field_items[idx]
                if fg.is_json_filter:
                    # Exact value match (=0, string values, bools)
                    self.dismiss(
                        FilterRule(
                            filter_type=FilterType.INCLUDE,
                            pattern=f"{fg.key}={fg.value}",
                            is_json_key=True,
                            json_key=fg.key,
                            json_value=fg.value,
                        )
                    )
                else:
                    # Synthetic group like >0: match non-zero values
                    self.dismiss(
                        FilterRule(
                            filter_type=FilterType.INCLUDE,
                            pattern=f'"{fg.key}": [1-9]',
                            is_regex=True,
                        )
                    )
        else:
            tmpl_items = self._sorted_template_groups()
            if 0 <= idx < len(tmpl_items):
                group = tmpl_items[idx]
                pattern = template_to_regex(group.content_pattern)
                self.dismiss(
                    FilterRule(
                        filter_type=FilterType.INCLUDE,
                        pattern=pattern,
                        is_regex=True,
                    )
                )

    def action_toggle_mode(self) -> None:
        self._mode = "fields" if self._mode == "messages" else "messages"
        # Reset sort to mode-appropriate default
        self._sort = "count"
        self._reverse = False
        self._rebuild_list()

    def action_cycle_sort(self) -> None:
        cycle = ["count", "level"] if self._mode == "messages" else ["count", "key"]
        idx = cycle.index(self._sort) if self._sort in cycle else 0
        self._sort = cycle[(idx + 1) % len(cycle)]
        self._rebuild_list()

    def action_reverse_order(self) -> None:
        self._reverse = not self._reverse
        self._rebuild_list()

    def action_cancel(self) -> None:
        self.dismiss(None)
