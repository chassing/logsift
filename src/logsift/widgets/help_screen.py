"""Help screen showing all keyboard shortcuts."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold]Navigation[/bold]
  Up/Down       Move between log lines
  PgUp/PgDn     Page up/down
  Home/End      Jump to first/last line
  gg            Jump to first line
  G             Jump to last line

[bold]Display[/bold]
  j             Toggle pretty-print for ALL JSON lines
  Enter         Toggle pretty-print for current line (sticky)
  n             Toggle line numbers

[bold]Filtering[/bold]
  /             Filter in (text or key=value)
  \\             Filter out (text or key=value)
  m             Manage filters (reorder, toggle, delete)
  c             Clear all filters
  1-9           Toggle individual filter on/off

  On JSON lines, / and \\ show key-value suggestions.
  Filters are auto-saved as sessions.

[bold]Tailing (--tail / -t)[/bold]
  p             Pause/resume tailing
  G             Jump to bottom (follow new lines)

  Pipe input is always tailed automatically.

[bold]Sessions[/bold]
  s             Save current filters as named session
  l             Load a saved session
  --session/-s  Load session on startup (CLI)

[bold]General[/bold]
  h, ?          Show this help
  q             Quit
"""


class HelpScreen(ModalScreen[None]):
    """Modal help screen with keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > VerticalScroll {
        width: 70;
        height: 80%;
        max-height: 30;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "dismiss_help", "Close"),
        ("h", "dismiss_help", "Close"),
        ("question_mark", "dismiss_help", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP_TEXT, markup=True)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
