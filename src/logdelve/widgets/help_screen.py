"""Help screen showing all keyboard shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

_COL_WIDTH = 38


def _k(bindings: dict[str, str], action: str) -> str:
    """Get human-readable display key for an action."""
    from logdelve.keybindings import format_key_display  # noqa: PLC0415

    return format_key_display(bindings.get(action, "?"))


def _line(keys: str, desc: str) -> str:
    return f"  {keys:<{_COL_WIDTH}}{desc}"


def _navigation_section(b: dict[str, str]) -> list[str]:
    return [
        "[bold]Navigation[/bold]",
        _line(f"{_k(b, 'cursor_up')}/{_k(b, 'cursor_down')}", "Move between log lines"),
        _line(f"{_k(b, 'page_up')}/{_k(b, 'page_down')}", "Page up/down"),
        _line(f"{_k(b, 'scroll_home')}/{_k(b, 'scroll_end')}", "Jump to first/last line"),
        _line(f"{_k(b, 'goto_top')}{_k(b, 'goto_top')}", "Jump to first line"),
        _line(_k(b, "scroll_bottom"), "Jump to last line"),
        _line(_k(b, "goto_line"), "Go to line number"),
        _line(_k(b, "jump_to_time"), "Jump to timestamp"),
        _line(_k(b, "prev_bookmark"), "Previous bookmark"),
        _line(_k(b, "next_bookmark"), "Next bookmark"),
        "",
    ]


def _bookmarks_section(b: dict[str, str]) -> list[str]:
    pb = _k(b, "prev_bookmark")
    display_pb = f"\\{pb}" if pb == "[" else pb
    return [
        "[bold]Bookmarks[/bold]",
        _line(_k(b, "toggle_bookmark"), "Toggle bookmark on current line"),
        _line(_k(b, "list_bookmarks"), "List bookmarks"),
        _line(_k(b, "annotate"), "Add/edit annotation"),
        _line(display_pb, "Previous bookmark"),
        _line(_k(b, "next_bookmark"), "Next bookmark"),
        "",
    ]


def _search_section(b: dict[str, str]) -> list[str]:
    sf = _k(b, "search_forward")
    sb = _k(b, "search_backward")
    gl = _k(b, "goto_line")
    jt = _k(b, "jump_to_time")
    return [
        "[bold]Search[/bold]",
        _line(sf, "Search forward"),
        _line(sb, "Search backward"),
        _line(_k(b, "next_match"), "Next match"),
        _line(_k(b, "prev_match"), "Previous match"),
        "",
        "  Search dialog has tabs: Search, Line, Time.",
        f"  {sf}, {sb}, {gl}, {jt} each open the respective tab.",
        "",
    ]


def _multi_pattern_section() -> list[str]:
    return [
        "[bold]Multi-Pattern Search[/bold]",
        _line("Enter (in dialog)", "Add / update pattern"),
        _line("Del", "Remove selected pattern"),
        _line("Ctrl+D", "Clear all patterns"),
        _line("Space (on pattern)", "Toggle n/N participation (\u25cf/\u25cb)"),
        _line("> (on pattern)", "Set as n/N navigation target"),
        "",
        "  Up to 10 patterns, each highlighted in a distinct color.",
        "  History dropdown shows recent patterns; select to restore.",
        "",
    ]


def _display_section(b: dict[str, str]) -> list[str]:
    return [
        "[bold]Display[/bold]",
        _line(_k(b, "toggle_json_global"), "Toggle pretty-print for ALL JSON lines"),
        _line(_k(b, "toggle_json_line"), "Toggle pretty-print for current line (sticky)"),
        _line(_k(b, "toggle_line_numbers"), "Toggle line numbers"),
        _line(_k(b, "cycle_component_display"), "Cycle component display (tag \u2192 full \u2192 off)"),
        "",
    ]


def _filtering_section(b: dict[str, str]) -> list[str]:
    fi = _k(b, "filter_in")
    fo = _k(b, "filter_out")
    return [
        "[bold]Filtering[/bold]",
        _line(f"{fi}/{fo}", "Filter in/out (text, key=value, regex, component, or time)"),
        _line(_k(b, "manage_filters"), "Manage filters (toggle, edit, delete, clear, reorder)"),
        _line(_k(b, "toggle_all_filters"), "Suspend/resume all filters"),
        _line(_k(b, "cycle_level_filter"), "Cycle log level filter (ALL \u2192 ERROR \u2192 WARN \u2192 INFO)"),
        _line(_k(b, "toggle_anomalies"), "Toggle anomaly-only filter (with --baseline)"),
        _line(_k(b, "show_related"), "Show related (trace/request ID correlation)"),
        _line("1-9", "Toggle individual filter on/off"),
        "",
        _line(_k(b, "analyze"), "Analyze message groups"),
        "",
        f"  On JSON lines, {fi} and {fo} show key-value suggestions.",
        "  When components are detected, a Component tab allows filtering by component.",
        "  Time tab allows filtering by timestamp range (start/end).",
        "  Filters are auto-saved as sessions.",
        "  CLI: --start/-S and --end/-E for time range on startup.",
        "",
    ]


def _remaining_sections(b: dict[str, str]) -> list[str]:
    return [
        "[bold]Export[/bold]",
        _line(_k(b, "export"), "Export filtered lines to file"),
        "  CLI: --output/-o FILE --format FORMAT (text, json, jsonl, csv)",
        "",
        "[bold]Tailing[/bold]",
        _line(_k(b, "toggle_tail_pause"), "Pause/resume tailing"),
        _line(_k(b, "scroll_bottom"), "Jump to bottom (follow new lines)"),
        "",
        "  Use --tail to follow a growing file. Pipe input is tailed automatically.",
        "",
        "[bold]Sessions[/bold]",
        _line(_k(b, "manage_sessions"), "Session manager (load, save, delete, rename)"),
        "  --session/-s                          Load session on startup (CLI)",
        "",
        "  Sessions save filters, bookmarks, search patterns, and history.",
        "",
        "[bold]Theme[/bold]",
        _line(_k(b, "toggle_theme"), "Select theme"),
        "",
        "[bold]General[/bold]",
        _line(_k(b, "show_help"), "Show this help"),
        _line(_k(b, "quit"), "Quit"),
    ]


def _build_help_text(bindings: dict[str, str]) -> str:
    """Build help text with actual configured key names."""
    sections: list[str] = []
    sections.extend(_navigation_section(bindings))
    sections.extend(_bookmarks_section(bindings))
    sections.extend(_search_section(bindings))
    sections.extend(_multi_pattern_section())
    sections.extend(_display_section(bindings))
    sections.extend(_filtering_section(bindings))
    sections.extend(_remaining_sections(bindings))
    return "\n".join(sections)


class HelpScreen(ModalScreen[None]):
    """Modal help screen with keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > VerticalScroll {
        width: 60%;
        height: 90%;
        max-height: 35;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "dismiss_help", "Close"),
        ("h", "dismiss_help", "Close"),
        ("q", "dismiss_help", "Close"),
    ]

    def __init__(self, bindings: dict[str, str] | None = None) -> None:
        super().__init__()
        self._key_bindings = bindings

    @override
    def compose(self) -> ComposeResult:
        from logdelve.keybindings import get_merged_bindings  # noqa: PLC0415

        resolved = self._key_bindings or get_merged_bindings()
        help_text = _build_help_text(resolved)
        with VerticalScroll():
            yield Static(help_text, markup=True)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
