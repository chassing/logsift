"""Modal dialog for search, go-to-line, and jump-to-timestamp."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, TabbedContent, TabPane

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.events import Key

from logdelve.models import SearchDirection, SearchQuery
from logdelve.widgets.timestamp_input import TimestampInput


class NavigationDialog(ModalScreen[SearchQuery | int | datetime | None]):
    """Modal dialog with tabs for Search, Go to Line, and Jump to Timestamp."""

    DEFAULT_CSS = """
    NavigationDialog {
        align: center middle;
    }

    NavigationDialog > Vertical {
        width: 80;
        height: 22;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    NavigationDialog > Vertical > .title {
        text-style: bold;
    }

    NavigationDialog > Vertical > TabbedContent {
        height: 1fr;
    }

    NavigationDialog Tabs {
        height: 4;
    }

    NavigationDialog .underline--bar {
        height: 0;
    }

    NavigationDialog Tab {
        height: 3;
        padding: 1 2 0 2;
    }

    NavigationDialog Tab.-active {
        text-style: bold;
        color: $text;
        border-top: round $primary;
        border-left: round $primary;
        border-right: round $primary;
        padding: 0 2;
    }

    NavigationDialog ContentSwitcher {
        height: 1fr;
        border: round $primary;
    }

    NavigationDialog TabPane {
        padding: 1 1 0 1;
    }

    NavigationDialog Input {
        width: 100%;
    }

    NavigationDialog Horizontal {
        height: auto;
        margin-top: 1;
    }

    NavigationDialog Horizontal > Checkbox {
        margin-right: 3;
    }

    NavigationDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        direction: SearchDirection,
        last_query: SearchQuery | None = None,
        initial_tab: str = "tab-search",
        reference_date: datetime | None = None,
    ) -> None:
        super().__init__()
        self._direction = direction
        self._last_query = last_query
        self._initial_tab = initial_tab
        self._reference_date = reference_date

    def compose(self) -> ComposeResult:
        self._titles = {
            "tab-search": "🔍 Search forward (/)" if self._direction == SearchDirection.FORWARD else "🔍 Search backward (?)",
            "tab-line": "Go to line (:)",
            "tab-time": "Jump to timestamp (@)",
        }
        label = self._titles.get(self._initial_tab, self._titles["tab-search"])
        with Vertical():
            yield Label(label, classes="title", id="dialog-title")

            with TabbedContent(id="nav-tabs", initial=self._initial_tab):
                with TabPane("Search", id="tab-search"):
                    yield from self._compose_search_tab()
                with TabPane("Line", id="tab-line"):
                    yield from self._compose_line_tab()
                with TabPane("Time", id="tab-time"):
                    yield from self._compose_time_tab()

            yield Label("Enter to apply, Escape to cancel", classes="hint")

    def _compose_search_tab(self) -> ComposeResult:
        initial_value = self._last_query.pattern if self._last_query else ""
        initial_case = self._last_query.case_sensitive if self._last_query else False
        initial_regex = self._last_query.is_regex if self._last_query else False
        yield Input(value=initial_value, placeholder="search pattern...", id="search-input")
        with Horizontal():
            yield Checkbox("Case sensitive", initial_case, id="case-sensitive")
            yield Checkbox("Regex", initial_regex, id="regex")

    @staticmethod
    def _compose_line_tab() -> ComposeResult:
        yield Input(placeholder="line number...", id="line-input")

    def _compose_time_tab(self) -> ComposeResult:
        yield TimestampInput(id="ts-widget", reference_date=self._reference_date)

    def on_mount(self) -> None:
        self._focus_active_tab_content()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Update the dialog title when switching tabs."""
        import contextlib  # noqa: PLC0415

        tab_id = event.pane.id or ""
        title = self._titles.get(tab_id, "")
        with contextlib.suppress(NoMatches):
            self.query_one("#dialog-title", Label).update(title)

    def _focus_active_tab_content(self) -> None:
        try:
            tabs = self.query_one("#nav-tabs", TabbedContent)
            active_pane = tabs.active_pane
            if active_pane is None:
                return
            if active_pane.id == "tab-time":
                import contextlib  # noqa: PLC0415

                with contextlib.suppress(NoMatches):
                    self.query_one("#ts-widget", TimestampInput).focus_input()
                return
            for child in active_pane.query("Input"):
                child.focus()
                return
        except NoMatches:
            pass

    def on_key(self, event: Key) -> None:
        """Handle Enter on checkboxes and TimestampInput."""
        focused = self.focused

        if event.key == "enter" and isinstance(focused, Checkbox):
            event.prevent_default()
            event.stop()
            self._submit_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id == "search-input":
            self._submit_search()
        elif input_id == "line-input":
            self._submit_line()
        elif input_id == "ts-input":
            self._submit_timestamp()

    def _submit_search(self) -> None:
        """Submit the search with current input and options."""
        try:
            inp = self.query_one("#search-input", Input)
        except NoMatches:
            self.dismiss(None)
            return

        pattern = inp.value.strip()
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

    def _submit_line(self) -> None:
        """Submit go-to-line."""
        try:
            inp = self.query_one("#line-input", Input)
        except NoMatches:
            self.dismiss(None)
            return

        raw = inp.value.strip()
        if not raw:
            self.dismiss(None)
            return

        try:
            line_number = int(raw)
        except ValueError:
            self.notify("Invalid line number", severity="error")
            return

        if line_number < 1:
            self.notify("Line number must be positive", severity="error")
            return

        self.dismiss(line_number)

    def _submit_timestamp(self) -> None:
        """Submit jump-to-timestamp."""
        try:
            ts_widget = self.query_one("#ts-widget", TimestampInput)
        except NoMatches:
            self.dismiss(None)
            return

        result = ts_widget.parse()
        if result is not None:
            self.dismiss(result)

    def action_cancel(self) -> None:
        self.dismiss(None)
