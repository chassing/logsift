"""Help screen showing all keyboard shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

HELP_TEXT = """\
[bold]Navigation[/bold]
  Up/Down                               Move between log lines
  PgUp/PgDn                             Page up/down
  Home/End                              Jump to first/last line
  gg                                    Jump to first line
  G                                     Jump to last line
  :                                     Go to line number
  @                                     Jump to timestamp

[bold]Search[/bold]
  /                                     Search forward
  ?                                     Search backward
  n                                     Next match
  N                                     Previous match

  Search dialog has tabs: Search, Line, Time.
  /, ?, :, @ each open the respective tab.

[bold]Display[/bold]
  j                                     Toggle pretty-print for ALL JSON lines
  Enter                                 Toggle pretty-print for current line (sticky)
  #                                     Toggle line numbers
  c                                     Cycle component display (tag → full → off)

[bold]Filtering[/bold]
  f                                     Filter in (text, key=value, regex, component, or time)
  F                                     Filter out (text, key=value, regex, component, or time)
  m                                     Manage filters (toggle, edit, delete, clear, reorder)
  x                                     Suspend/resume all filters
  e                                     Cycle log level filter (ALL → ERROR → WARN → INFO)
  !                                     Toggle anomaly-only filter (with --baseline)
  1-9                                   Toggle individual filter on/off

  a                                     Analyze message groups

  On JSON lines, f and F show key-value suggestions.
  When components are detected, a Component tab allows filtering by component.
  Time tab allows filtering by timestamp range (start/end).
  Filters are auto-saved as sessions.
  CLI: --start/-S and --end/-E for time range on startup.

[bold]Tailing[/bold]
  p                                     Pause/resume tailing
  G                                     Jump to bottom (follow new lines)

  Use --tail to follow a growing file. Pipe input is tailed automatically.

[bold]Sessions[/bold]
  s                                     Session manager (load, save, delete, rename)
  --session/-s                          Load session on startup (CLI)

[bold]Theme[/bold]
  t                                     Select theme

[bold]General[/bold]
  h                                     Show this help
  q                                     Quit
"""


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

    @override
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP_TEXT, markup=True)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
