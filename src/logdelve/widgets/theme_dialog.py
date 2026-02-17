"""Modal dialog for theme selection."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType


class ThemeDialog(ModalScreen[str | None]):
    """Modal dialog for selecting a theme from all available Textual themes."""

    DEFAULT_CSS = """
    ThemeDialog {
        align: center middle;
    }

    ThemeDialog > Vertical {
        width: 50%;
        height: 60%;
        max-height: 80%;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    ThemeDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    ThemeDialog > Vertical > OptionList {
        height: 1fr;
        max-height: 20;
    }

    ThemeDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_theme: str) -> None:
        super().__init__()
        self._current_theme = current_theme

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        with Vertical():
            yield Label("🎨 Select theme", classes="title")
            yield OptionList(id="theme-list")
            yield Label("Enter to select, Escape to cancel", classes="hint")

    def on_mount(self) -> None:
        ol = self.query_one("#theme-list", OptionList)
        theme_names = sorted(self.app.available_themes.keys())
        current_idx = 0
        for i, name in enumerate(theme_names):
            display = Text()
            if name == self._current_theme:
                display.append(f"● {name}", style="bold green")
                current_idx = i
            else:
                display.append(f"  {name}")
            ol.add_option(Option(display, id=name))
        ol.highlighted = current_idx

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        theme_id = str(event.option.id)
        self.dismiss(theme_id)

    def action_cancel(self) -> None:
        self.dismiss(None)
