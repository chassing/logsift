"""Textual application for logsift."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer

from logsift.models import FilterRule, FilterType, LogLine
from logsift.widgets.filter_bar import FilterBar
from logsift.widgets.filter_dialog import FilterDialog
from logsift.widgets.help_screen import HelpScreen
from logsift.widgets.log_view import LogView
from logsift.widgets.status_bar import StatusBar


class LogSiftApp(App[None]):
    """Log viewer TUI application."""

    CSS_PATH = "styles/app.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help"),
        Binding("h", "show_help", "Help", show=False),
        Binding("slash", "filter_in", "Filter in"),
        Binding("backslash", "filter_out", "Filter out"),
        Binding("c", "clear_filters", "Clear filters"),
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

    def __init__(self, lines: list[LogLine] | None = None, source: str = "") -> None:
        super().__init__()
        self._lines = lines or []
        self._source = source
        self._filter_rules: list[FilterRule] = []

    def compose(self) -> ComposeResult:
        yield FilterBar(id="filter-bar")
        yield LogView(id="log-view")
        yield StatusBar(source=self._source, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        if self._lines:
            log_view.set_lines(self._lines)
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        status_bar = self.query_one("#status-bar", StatusBar)
        if log_view.has_filters:
            status_bar.update_counts(log_view.total_count, log_view.filtered_count)
        else:
            status_bar.update_counts(log_view.total_count)

    def _apply_filters(self) -> None:
        log_view = self.query_one("#log-view", LogView)
        filter_bar = self.query_one("#filter-bar", FilterBar)
        log_view.set_filters(self._filter_rules)
        filter_bar.update_filters(self._filter_rules)
        self._update_status_bar()

    def _add_filter(self, rule: FilterRule) -> None:
        self._filter_rules.append(rule)
        self._apply_filters()

    def action_filter_in(self) -> None:
        self.push_screen(FilterDialog(FilterType.INCLUDE), callback=self._on_filter_result)

    def action_filter_out(self) -> None:
        self.push_screen(FilterDialog(FilterType.EXCLUDE), callback=self._on_filter_result)

    def _on_filter_result(self, result: FilterRule | None) -> None:
        if result is not None:
            self._add_filter(result)

    def action_clear_filters(self) -> None:
        if self._filter_rules:
            self._filter_rules.clear()
            self._apply_filters()

    def action_toggle_filter(self, index: int) -> None:
        idx = index - 1
        if 0 <= idx < len(self._filter_rules):
            self._filter_rules[idx].enabled = not self._filter_rules[idx].enabled
            self._apply_filters()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())
