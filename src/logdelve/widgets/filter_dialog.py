"""Modal dialog for entering filter patterns."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, SelectionList, TabbedContent, TabPane

if TYPE_CHECKING:
    from datetime import datetime

    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.events import Key

from logdelve.filters import flatten_json
from logdelve.models import FilterRule, FilterType
from logdelve.widgets.timestamp_input import TimestampInput


class FilterDialog(ModalScreen[FilterRule | list[FilterRule] | None]):
    """Modal dialog for entering a filter pattern.

    Supports text patterns, key=value syntax for JSON key filters, regex,
    and component selection via tabs.
    When components are provided, shows a tabbed interface with Text and Component tabs.
    Returns a single FilterRule (text/json) or list[FilterRule] (components/json keys) or None.
    """

    DEFAULT_CSS = """
    FilterDialog {
        align: center middle;
    }

    FilterDialog > Vertical {
        width: 90%;
        height: 80%;
        max-height: 40;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    FilterDialog > Vertical > .title {
        text-style: bold;
    }

    FilterDialog > Vertical > TabbedContent {
        height: 1fr;
    }

    FilterDialog Tabs {
        height: 4;
    }

    FilterDialog .underline--bar {
        height: 0;
    }

    FilterDialog Tab {
        height: 3;
        padding: 1 2 0 2;
    }

    FilterDialog Tab.-active {
        text-style: bold;
        color: $text;
        border-top: round $primary;
        border-left: round $primary;
        border-right: round $primary;
        padding: 0 2;
    }

    FilterDialog ContentSwitcher {
        height: 1fr;
        border: round $primary;
    }

    FilterDialog TabPane {
        padding: 1 1 0 1;
    }

    FilterDialog #json-keys {
        height: auto;
        max-height: 14;
    }

    FilterDialog #component-list {
        height: 1fr;
    }

    FilterDialog Input {
        width: 100%;
        margin-top: 1;
    }

    FilterDialog Horizontal {
        height: auto;
        margin-top: 1;
    }

    FilterDialog Horizontal > Checkbox {
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

    def __init__(
        self,
        filter_type: FilterType,
        json_data: dict[str, Any] | None = None,
        components: dict[str, int] | None = None,
        reference_date: datetime | None = None,
    ) -> None:
        super().__init__()
        self._filter_type = filter_type
        self._json_data = json_data
        self._pairs: list[tuple[str, str]] = []
        self._components = components or {}
        self._component_names: list[str] = []
        self._reference_date = reference_date

    def compose(self) -> ComposeResult:
        label = "Filter in (show matching)" if self._filter_type == FilterType.INCLUDE else "Filter out (hide matching)"
        with Vertical():
            yield Label(label, classes="title")

            with TabbedContent(id="filter-tabs", initial="tab-text"):
                with TabPane("Text", id="tab-text"):
                    yield from self._compose_text_tab()
                if self._components:
                    with TabPane("Component", id="tab-component"):
                        yield from self._compose_component_tab()
                with TabPane("Time", id="tab-time"):
                    yield from self._compose_time_tab()

            yield Label("Space to toggle, Enter to apply, Escape to cancel", classes="hint")

    def _compose_text_tab(self) -> ComposeResult:
        if self._json_data:
            self._pairs = flatten_json(self._json_data)
            selections: list[tuple[str, str]] = []
            for key, value in self._pairs:
                selections.append((f"{key} = {value}", f"{key}={value}"))
            yield SelectionList[str](*selections, id="json-keys")

        yield Input(
            placeholder="text pattern or key=value...",
            id="filter-input",
        )
        with Horizontal():
            yield Checkbox("Case sensitive", id="case-sensitive")
            yield Checkbox("Regex", id="regex")

    def _compose_component_tab(self) -> ComposeResult:
        self._component_names = sorted(self._components.keys())
        selections: list[tuple[str, str]] = []
        for name in self._component_names:
            count = self._components[name]
            selections.append((f"{name}  ({count:,} lines)", name))
        yield SelectionList[str](*selections, id="component-list")

    def _compose_time_tab(self) -> ComposeResult:
        yield Label("Start (inclusive):", classes="hint")
        yield TimestampInput(id="time-start", reference_date=self._reference_date)
        yield Label("End (exclusive):", classes="hint")
        yield TimestampInput(id="time-end", reference_date=self._reference_date)

    def on_mount(self) -> None:
        self._focus_active_tab_content()

    def on_key(self, event: Key) -> None:
        """Handle key events for form submission."""
        focused = self.focused

        # Enter on checkboxes submits the text filter
        if event.key == "enter" and isinstance(focused, Checkbox):
            event.prevent_default()
            event.stop()
            self._submit_text_filter()
            return

        # Enter on SelectionList submits the selected items
        if event.key == "enter" and isinstance(focused, SelectionList):
            event.prevent_default()
            event.stop()
            if focused.id == "json-keys":
                self._submit_json_key_filter()
            elif focused.id == "component-list":
                self._submit_component_filter()

    def _focus_active_tab_content(self) -> None:
        """Focus the first focusable widget in the active tab pane."""
        with contextlib.suppress(NoMatches):
            tabs = self.query_one("#filter-tabs", TabbedContent)
            active_pane = tabs.active_pane
            if active_pane is None:
                return
            for child in active_pane.query("*"):
                if child.focusable:
                    child.focus()
                    if isinstance(child, SelectionList) and child.option_count > 0:
                        child.highlighted = 0
                    return

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        try:
            tabs = self.query_one("#filter-tabs", TabbedContent)
            active = tabs.active_pane
            if active is not None and active.id == "tab-time":
                self._submit_time_range()
                return
        except NoMatches:
            pass
        self._submit_text_filter()

    def _submit_text_filter(self) -> None:
        """Submit the filter with current input and options."""
        try:
            inp = self.query_one("#filter-input", Input)
        except NoMatches:
            self.dismiss(None)
            return

        pattern = inp.value.strip()
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

    def _submit_json_key_filter(self) -> None:
        """Submit JSON key filters for all selected key-value pairs."""
        try:
            sl = self.query_one("#json-keys", SelectionList)
        except NoMatches:
            self.dismiss(None)
            return

        selected = list(sl.selected)
        if not selected:
            self.dismiss(None)
            return

        rules: list[FilterRule] = []
        for kv_str in selected:
            key, _, value = kv_str.partition("=")
            rules.append(
                FilterRule(
                    filter_type=self._filter_type,
                    pattern=kv_str,
                    is_json_key=True,
                    json_key=key,
                    json_value=value,
                )
            )
        self.dismiss(rules)

    def _submit_component_filter(self) -> None:
        """Submit component filters for all selected components."""
        try:
            sl = self.query_one("#component-list", SelectionList)
        except NoMatches:
            self.dismiss(None)
            return

        selected = list(sl.selected)
        if not selected:
            self.dismiss(None)
            return

        rules = [
            FilterRule(
                filter_type=self._filter_type,
                pattern=f"component:{name}",
                is_component=True,
                component_name=name,
            )
            for name in selected
        ]
        self.dismiss(rules)

    def _submit_time_range(self) -> None:
        """Submit a time range filter from start/end TimestampInput widgets."""
        try:
            start_widget = self.query_one("#time-start", TimestampInput)
            end_widget = self.query_one("#time-end", TimestampInput)
        except NoMatches:
            self.dismiss(None)
            return

        start_raw = start_widget.value
        end_raw = end_widget.value

        if not start_raw and not end_raw:
            self.dismiss(None)
            return

        # Parse and resolve to absolute timestamps
        start_iso: str | None = None
        end_iso: str | None = None

        if start_raw:
            start_result = start_widget.parse()
            if start_result is None:
                return
            start_iso = start_result.isoformat()

        if end_raw:
            end_result = end_widget.parse()
            if end_result is None:
                return
            end_iso = end_result.isoformat()

        # Build display pattern (show user's input, not ISO)
        if start_raw and end_raw:
            pattern = f"Time: {start_raw} - {end_raw}"
        elif start_raw:
            pattern = f"Time: after {start_raw}"
        else:
            pattern = f"Time: before {end_raw}"

        self.dismiss(
            FilterRule(
                filter_type=self._filter_type,
                pattern=pattern,
                is_time_range=True,
                time_start=start_iso,
                time_end=end_iso,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
