"""Unified session management dialog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from logdelve.session import delete_session, list_sessions, rename_session

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType


class SessionActionType(StrEnum):
    """Possible session dialog actions."""

    LOAD = "load"
    SAVE = "save"
    RENAME = "rename"


@dataclass
class SessionAction:
    """Result from the session management dialog."""

    action: SessionActionType
    name: str


class SessionManageDialog(ModalScreen[SessionAction | None]):
    """Unified session management: load, save, delete, rename."""

    DEFAULT_CSS = """
    SessionManageDialog {
        align: center middle;
    }

    SessionManageDialog > Vertical {
        width: 70;
        height: 80%;
        max-height: 25;
        background: $surface;
        border: tall $accent;
        padding: 1 2;
    }

    SessionManageDialog > Vertical > .title {
        margin-bottom: 1;
        text-style: bold;
    }

    SessionManageDialog > Vertical > OptionList {
        height: 1fr;
    }

    SessionManageDialog > Vertical > Input {
        width: 100%;
        margin-top: 1;
    }

    SessionManageDialog > Vertical > .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Close"),
        Binding("q", "cancel", "Close"),
        Binding("d", "delete_session", "Delete"),
        Binding("r", "rename_session", "Rename"),
    ]

    def __init__(self, current_session: str | None = None) -> None:
        super().__init__()
        self._original_session = current_session
        self._current_session = current_session
        self._renaming: str | None = None

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        with Vertical():
            yield Label("Session manager", classes="title")
            yield OptionList(id="session-list")
            yield Input(placeholder="Type name + Enter to save new session...", id="save-input")
            yield Label("Enter: load  d: delete  r: rename  Esc: close", classes="hint")

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        ol = self.query_one("#session-list", OptionList)
        highlighted = ol.highlighted
        ol.clear_options()
        sessions = list_sessions()
        if sessions:
            for name in sessions:
                display = Text()
                if name == self._current_session:
                    display.append(name, style="bold green")
                    display.append(" (active)", style="dim green")
                else:
                    display.append(name)
                ol.add_option(Option(display, id=name))
        else:
            ol.add_option(Option("(no saved sessions)", disabled=True))
        if highlighted is not None and sessions:
            ol.highlighted = min(highlighted, len(sessions) - 1)

    def _get_selected_name(self) -> str | None:
        ol = self.query_one("#session-list", OptionList)
        if ol.highlighted is None:
            return None
        option = ol.get_option_at_index(ol.highlighted)
        return str(option.id) if option.id and not str(option.id).startswith("(") else None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Load a session when Enter is pressed on the OptionList."""
        if self._renaming:
            return
        name = self._get_selected_name()
        if name:
            self.dismiss(SessionAction(SessionActionType.LOAD, name))

    def action_delete_session(self) -> None:
        if self._renaming:
            return
        name = self._get_selected_name()
        if name:
            delete_session(name)
            self.notify(f"Session '{name}' deleted")
            self._rebuild_list()

    def action_rename_session(self) -> None:
        name = self._get_selected_name()
        if not name:
            return
        self._renaming = name
        inp = self.query_one("#save-input", Input)
        inp.value = name
        inp.placeholder = f"Rename '{name}' to..."
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_name = event.value.strip()
        if not new_name:
            return

        if self._renaming:
            old_name = self._renaming
            rename_session(old_name, new_name)
            self.notify(f"Renamed '{old_name}' to '{new_name}'")
            if old_name == self._current_session:
                self._current_session = new_name
            self._renaming = None
            inp = self.query_one("#save-input", Input)
            inp.value = ""
            inp.placeholder = "Save as new session name..."
            self._rebuild_list()
            self.query_one("#session-list", OptionList).focus()
        else:
            self.dismiss(SessionAction(SessionActionType.SAVE, new_name))

    def action_cancel(self) -> None:
        if self._renaming:
            self._renaming = None
            inp = self.query_one("#save-input", Input)
            inp.value = ""
            inp.placeholder = "Save as new session name..."
            self.query_one("#session-list", OptionList).focus()
        elif self._current_session != self._original_session:
            self.dismiss(SessionAction(SessionActionType.RENAME, self._current_session or ""))
        else:
            self.dismiss(None)
