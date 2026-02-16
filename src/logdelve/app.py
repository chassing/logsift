"""Textual application for logdelve."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer
from textual.worker import get_current_worker

from logdelve.config import load_config, save_config
from logdelve.models import ContentType, FilterRule, FilterType, LogLine, SearchDirection, SearchQuery
from logdelve.reader import read_file_async, read_pipe_async
from logdelve.session import create_session, load_session, save_session
from logdelve.widgets.filter_bar import FilterBar
from logdelve.widgets.filter_dialog import FilterDialog
from logdelve.widgets.filter_manage_dialog import FilterManageDialog
from logdelve.widgets.help_screen import HelpScreen
from logdelve.widgets.log_view import LogView
from logdelve.widgets.search_dialog import SearchDialog
from logdelve.widgets.session_dialog import SessionAction, SessionManageDialog
from logdelve.widgets.status_bar import StatusBar
from logdelve.widgets.theme_dialog import ThemeDialog


class LogDelveApp(App[None]):
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("slash", "search_forward", "Search"),
        Binding("question_mark", "search_backward", "Search back"),
        Binding("f", "filter_in", "Filter in"),
        Binding("F", "filter_out", "Filter out"),
        Binding("m", "manage_filters", "Filters"),
        Binding("s", "manage_sessions", "Sessions"),
        Binding("t", "toggle_theme", "Theme"),
        Binding("q", "quit", "Quit", show=False),
        Binding("p", "toggle_tail_pause", "Pause"),
        Binding("h", "show_help", "Help"),
        Binding("1", "toggle_filter(1)", "Toggle 1", show=False),
        Binding("2", "toggle_filter(2)", "Toggle 2", show=False),
        Binding("3", "toggle_filter(3)", "Toggle 3", show=False),
        Binding("4", "toggle_filter(4)", "Toggle 4", show=False),
        Binding("5", "toggle_filter(5)", "Toggle 5", show=False),
        Binding("6", "toggle_filter(6)", "Toggle 6", show=False),
        Binding("7", "toggle_filter(7)", "Toggle 7", show=False),
        Binding("8", "toggle_filter(8)", "Toggle 8", show=False),
        Binding("9", "toggle_filter(9)", "Toggle 9", show=False),
    ]

    def __init__(
        self,
        lines: list[LogLine] | None = None,
        source: str = "",
        session_name: str | None = None,
        file_path: Path | None = None,
        tail: bool = False,
        pipe_fd: int | None = None,
    ) -> None:
        super().__init__()
        self._lines = lines or []
        self._source = source
        self._filter_rules: list[FilterRule] = []
        self._session_name = session_name or datetime.now(tz=UTC).strftime("%Y-%m-%d-%H%M%S")
        self._file_path = file_path
        self._tail = tail
        self._pipe_fd = pipe_fd
        self._tail_paused: bool = False
        self._tail_buffer: list[LogLine] = []
        self._last_search: SearchQuery | None = None
        self._config = load_config()
        self.theme = self._config.theme

    @property
    def _is_streaming(self) -> bool:
        return self._tail or self._pipe_fd is not None

    def compose(self) -> ComposeResult:
        yield FilterBar(id="filter-bar")
        yield LogView(id="log-view")
        yield StatusBar(source=self._source, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._lines:
            log_view.set_lines(self._lines)

        if self._session_name:
            try:
                session = load_session(self._session_name)
                self._filter_rules = list(session.filters)
                self._apply_filters()
                self.notify(f"Session '{self._session_name}' loaded")
            except FileNotFoundError:
                pass

        if self._tail and self._file_path:
            status_bar.set_tailing(True)
            self.run_worker(self._tail_worker(read_file_async(self._file_path, tail=True)), exclusive=True)
        elif self._pipe_fd is not None:
            status_bar.set_tailing(True)
            self.run_worker(self._tail_worker(read_pipe_async(self._pipe_fd)), exclusive=True)

        self._update_status_bar()

    async def _tail_worker(self, reader: AsyncIterator[LogLine]) -> None:
        """Consume async line reader and append lines to the view."""
        log_view = self.query_one("#log-view", LogView)
        worker = get_current_worker()
        async for line in reader:
            if worker.is_cancelled:
                break
            if self._tail_paused:
                self._tail_buffer.append(line)
                status_bar = self.query_one("#status-bar", StatusBar)
                status_bar.set_new_lines(len(self._tail_buffer))
            else:
                log_view.append_line(line)
                self._update_status_bar()

    def action_toggle_tail_pause(self) -> None:
        """Toggle tail pause/resume."""
        if not self._is_streaming:
            return
        self._tail_paused = not self._tail_paused
        status_bar = self.query_one("#status-bar", StatusBar)

        if self._tail_paused:
            status_bar.set_tailing(False)
            self.notify("Tailing paused")
        else:
            log_view = self.query_one("#log-view", LogView)
            for line in self._tail_buffer:
                log_view.append_line(line)
            self._tail_buffer.clear()
            status_bar.set_tailing(True)
            status_bar.set_new_lines(0)
            self._update_status_bar()
            self.notify("Tailing resumed")

    def _update_status_bar(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        if log_view.has_filters:
            status_bar.update_counts(log_view.total_count, log_view.filtered_count)
        else:
            status_bar.update_counts(log_view.total_count)

    def _update_search_status(self) -> None:
        """Update status bar with current search match info."""
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        if log_view.search_match_count > 0:
            status_bar.set_search_info(log_view.search_current_index + 1, log_view.search_match_count)
        elif log_view.has_search:
            status_bar.set_search_info(0, 0)
        else:
            status_bar.clear_search_info()

    def _apply_filters(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        filter_bar = self.query_one("#filter-bar", FilterBar)
        log_view.set_filters(self._filter_rules)
        filter_bar.update_filters(self._filter_rules)
        self._update_status_bar()
        self._autosave_filters()

    def _autosave_filters(self) -> None:
        """Auto-save current filters under session name."""
        if not self._filter_rules:
            return
        session = create_session(self._session_name, self._filter_rules)
        save_session(session)

    def _add_filter(self, rule: FilterRule) -> None:
        self._filter_rules.append(rule)
        self._apply_filters()

    def _get_current_json_data(self) -> dict[str, Any] | None:
        """Get JSON data from the current cursor line, if it's a JSON line."""
        log_view = self.query_one("#log-view", LogView)
        visible = log_view._lines
        if not visible:
            return None
        line = visible[log_view.cursor_line]
        if line.content_type == ContentType.JSON and line.parsed_json is not None:
            return line.parsed_json
        return None

    # --- Search actions ---

    def action_search_forward(self) -> None:
        self.push_screen(SearchDialog(SearchDirection.FORWARD), callback=self._on_search_result)

    def action_search_backward(self) -> None:
        self.push_screen(SearchDialog(SearchDirection.BACKWARD), callback=self._on_search_result)

    def _on_search_result(self, result: SearchQuery | None) -> None:
        if result is None:
            return
        self._last_search = result
        log_view = self.query_one("#log-view", LogView)
        log_view.set_search(result)
        self._update_search_status()

    # --- Filter actions ---

    def action_filter_in(self) -> None:
        json_data = self._get_current_json_data()
        self.push_screen(FilterDialog(FilterType.INCLUDE, json_data=json_data), callback=self._on_filter_result)

    def action_filter_out(self) -> None:
        json_data = self._get_current_json_data()
        self.push_screen(FilterDialog(FilterType.EXCLUDE, json_data=json_data), callback=self._on_filter_result)

    def _on_filter_result(self, result: FilterRule | None) -> None:
        if result is not None:
            self._add_filter(result)

    def action_manage_filters(self) -> None:
        if not self._filter_rules:
            self.notify("No filters to manage", severity="warning")
            return
        self.push_screen(FilterManageDialog(self._filter_rules), callback=self._on_manage_result)

    def _on_manage_result(self, result: list[FilterRule] | None) -> None:
        if result is not None:
            self._filter_rules = result
            self._apply_filters()

    def action_toggle_filter(self, index: int) -> None:
        idx = index - 1
        if 0 <= idx < len(self._filter_rules):
            self._filter_rules[idx].enabled = not self._filter_rules[idx].enabled
            self._apply_filters()

    # --- Session actions ---

    def action_manage_sessions(self) -> None:
        self.push_screen(SessionManageDialog(current_session=self._session_name), callback=self._on_session_result)

    def _on_session_result(self, result: SessionAction | None) -> None:
        if result is None:
            return
        if result.action == "load":
            try:
                session = load_session(result.name)
            except FileNotFoundError:
                self.notify(f"Session '{result.name}' not found", severity="error")
                return
            self._session_name = result.name
            self._filter_rules = list(session.filters)
            self._apply_filters()
            self.notify(f"Session '{result.name}' loaded")
        elif result.action == "save":
            if not self._filter_rules:
                self.notify("No filters to save", severity="warning")
                return
            self._session_name = result.name
            session = create_session(result.name, self._filter_rules)
            save_session(session)
            self.notify(f"Session '{result.name}' saved")

    # --- Theme ---

    def action_toggle_theme(self) -> None:
        """Open theme selection dialog."""
        self.push_screen(ThemeDialog(self.theme), callback=self._on_theme_result)

    def _on_theme_result(self, result: str | None) -> None:
        if result is None:
            return
        self.theme = result
        self._config.theme = result
        save_config(self._config)

    # --- Help ---

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide pause binding when not streaming."""
        if action == "toggle_tail_pause":
            return True if self._is_streaming else None
        return True
