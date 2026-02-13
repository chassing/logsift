"""Modal dialogs for session save and load."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from logsift.session import list_sessions


class SessionSaveDialog(ModalScreen[str | None]):
    """Modal dialog for saving a session with a name."""

    DEFAULT_CSS = """
    SessionSaveDialog {
        align: center middle;
    }

    SessionSaveDialog > Vertical {
        width: 60;
        height: auto;
        max-height: 12;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    SessionSaveDialog > Vertical > Label {
        margin-bottom: 1;
        text-style: bold;
    }

    SessionSaveDialog > Vertical > Input {
        width: 100%;
    }

    SessionSaveDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Save session as")
            yield Input(placeholder="Session name...", id="session-name")
            yield Label("Enter to save, Escape to cancel", classes="hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name:
            self.dismiss(name)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SessionLoadDialog(ModalScreen[str | None]):
    """Modal dialog for loading a saved session."""

    DEFAULT_CSS = """
    SessionLoadDialog {
        align: center middle;
    }

    SessionLoadDialog > Vertical {
        width: 60;
        height: 80%;
        max-height: 20;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    SessionLoadDialog > Vertical > Label {
        margin-bottom: 1;
        text-style: bold;
    }

    SessionLoadDialog > Vertical > OptionList {
        height: 1fr;
    }

    SessionLoadDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        sessions = list_sessions()
        with Vertical():
            yield Label("Load session")
            ol = OptionList(id="session-list")
            if sessions:
                for name in sessions:
                    ol.add_option(Option(name))
            else:
                ol.add_option(Option("(no saved sessions)", disabled=True))
            yield ol
            yield Label("Enter to load, Escape to cancel", classes="hint")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        prompt = event.option.prompt
        if isinstance(prompt, str) and not prompt.startswith("("):
            self.dismiss(prompt)

    def action_cancel(self) -> None:
        self.dismiss(None)
