"""Keybinding registry, normalization, validation, and defaults generation.

This module is the single source of truth for all configurable keybindings.
It maps action names to their default Textual keys, normalizes user-provided
key aliases to canonical names, validates user overrides, builds keymap dicts
for Textual's ``set_keymap()``, and generates TOML defaults output.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Binding registry: action_name -> default Textual key
# ---------------------------------------------------------------------------

DEFAULT_BINDINGS: dict[str, str] = {
    # App-level bindings (from app.py)
    "manage_sessions": "s",
    "toggle_all_filters": "x",
    "search_forward": "slash",
    "search_backward": "question_mark",
    "goto_line": "colon",
    "jump_to_time": "at",
    "filter_in": "f",
    "filter_out": "F",
    "toggle_bookmark": "b",
    "list_bookmarks": "B",
    "prev_bookmark": "left_square_bracket",
    "next_bookmark": "right_square_bracket",
    "annotate": "A",
    "show_related": "r",
    "export": "ctrl+e",
    "analyze": "a",
    "manage_filters": "m",
    "toggle_theme": "t",
    "cycle_level_filter": "e",
    "toggle_anomalies": "exclamation_mark",
    "quit": "q",
    "toggle_tail_pause": "p",
    "show_help": "h",
    "save_screenshot_svg": "ctrl+s",
    # LogView-level bindings (from log_view.py)
    "cursor_up": "up",
    "cursor_down": "down",
    "page_up": "pageup",
    "page_down": "pagedown",
    "scroll_home": "home",
    "scroll_end": "end",
    "goto_top": "g",
    "scroll_bottom": "G",
    "toggle_json_global": "j",
    "toggle_json_line": "enter",
    "toggle_line_numbers": "hash",
    "cycle_component_display": "c",
    "next_match": "n",
    "prev_match": "N",
}

# ---------------------------------------------------------------------------
# Key alias map: user-friendly symbol -> Textual canonical name
# ---------------------------------------------------------------------------

_KEY_ALIASES: dict[str, str] = {
    "/": "slash",
    "?": "question_mark",
    "!": "exclamation_mark",
    "#": "hash",
    "@": "at",
    ":": "colon",
    "[": "left_square_bracket",
    "]": "right_square_bracket",
    ";": "semicolon",
    "'": "apostrophe",
    ",": "comma",
    ".": "full_stop",
    "-": "minus",
    "=": "equals",
    "`": "grave_accent",
    "\\": "backslash",
    "<": "less_than_sign",
    ">": "greater_than_sign",
}

# Reverse map for display: canonical name -> user-friendly symbol
_DISPLAY_MAP: dict[str, str] = {v: k for k, v in _KEY_ALIASES.items()}

# Protected keys that cannot be rebound
_PROTECTED_KEYS: frozenset[str] = frozenset({"tab", "escape", "ctrl+c", "ctrl+q"})

# Pattern for valid snake_case action names
_SNAKE_CASE_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# Pattern for valid key format (letters, digits, underscore, plus for modifiers)
_VALID_KEY_RE: re.Pattern[str] = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9_]*$"  # Simple keys like "f", "pageup", "home"
    r"|^[a-z]+\+[a-zA-Z0-9_]+$"  # Modifier keys like "ctrl+f", "shift+a"
)


def normalize_key(key: str) -> str:
    """Normalize a key alias to its Textual canonical name.

    Maps user-friendly symbols (``/``, ``?``, ``#``, etc.) to their
    Textual canonical names (``slash``, ``question_mark``, ``hash``).
    Already-canonical names pass through unchanged.
    """
    return _KEY_ALIASES.get(key, key)


def normalize_keybindings(raw: dict[str, str]) -> dict[str, str]:
    """Normalize all key values in a keybindings dict."""
    return {action: normalize_key(key) for action, key in raw.items()}


def _validate_action_names(user_bindings: dict[str, str]) -> tuple[list[str], set[str]]:
    """Validate action names are snake_case and known."""
    errors: list[str] = []
    valid_actions: set[str] = set()
    for action in user_bindings:
        if not _SNAKE_CASE_RE.match(action):
            errors.append(f"Error: Action name '{action}' must be snake_case")
        elif action not in DEFAULT_BINDINGS:
            errors.append(f"Error: Unknown action '{action}'")
        else:
            valid_actions.add(action)
    return errors, valid_actions


def _validate_key_values(
    user_bindings: dict[str, str],
    valid_actions: set[str],
) -> list[str]:
    """Validate key values for protected keys and format."""
    errors: list[str] = []
    for action in valid_actions:
        key = user_bindings[action]
        if key in _PROTECTED_KEYS:
            errors.append(f"Error: Cannot rebind protected key '{key}' (action: {action})")
        if not key or not _VALID_KEY_RE.match(key):
            errors.append(f"Error: Invalid key format '{key}' (action: {action})")
    return errors


def _validate_duplicate_keys(
    user_bindings: dict[str, str],
    valid_actions: set[str],
) -> list[str]:
    """Check for duplicate keys within user config and cross-conflicts with defaults."""
    errors: list[str] = []

    # Duplicate keys within user config
    key_to_actions: dict[str, list[str]] = {}
    for action in valid_actions:
        key_to_actions.setdefault(user_bindings[action], []).append(action)
    for key, actions in sorted(key_to_actions.items()):
        if len(actions) > 1:
            errors.append(f"Error: Duplicate key '{key}': {', '.join(sorted(actions))}")

    # Cross-conflicts with defaults
    merged = get_merged_bindings(user_bindings)
    reverse: dict[str, list[str]] = {}
    for action, key in merged.items():
        reverse.setdefault(key, []).append(action)
    for key, actions in sorted(reverse.items()):
        if len(actions) <= 1:
            continue
        custom = [a for a in actions if a in valid_actions]
        default = [a for a in actions if a not in valid_actions]
        if custom and default:
            errors.append(
                f"Error: Key '{key}' conflicts: "
                f"{', '.join(sorted(custom))} (custom), "
                f"{', '.join(sorted(default))} (default)"
            )
    return errors


def validate_keybindings(user_bindings: dict[str, str]) -> list[str]:
    """Validate user keybinding overrides.

    Returns a list of error strings (empty list means valid).
    All errors are collected before returning so the user can fix
    everything in one pass.
    """
    name_errors, valid_actions = _validate_action_names(user_bindings)
    key_errors = _validate_key_values(user_bindings, valid_actions)
    dup_errors = _validate_duplicate_keys(user_bindings, valid_actions)
    return name_errors + key_errors + dup_errors


def build_keymap(user_bindings: dict[str, str]) -> dict[str, str]:
    """Build a keymap dict for Textual's ``set_keymap()``.

    Takes validated, normalized user bindings and returns a mapping
    of ``binding_id`` -> ``new_key``. Since binding IDs match action
    names by convention, this returns only the overridden entries.
    """
    return dict(user_bindings)


def generate_defaults_toml() -> str:
    """Generate a TOML string with all default keybindings.

    Output starts with ``[keybindings]`` header and lists all
    actions sorted alphabetically with their default keys.
    Ready to paste into ``~/.config/logdelve/config.toml``.
    """
    lines = ["[keybindings]"]
    for action in sorted(DEFAULT_BINDINGS):
        key = DEFAULT_BINDINGS[action]
        lines.append(f'{action} = "{key}"')
    return "\n".join(lines) + "\n"


def get_merged_bindings(
    user_bindings: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return the full action->key mapping with user overrides applied.

    Unspecified actions retain their default keys.
    """
    merged = dict(DEFAULT_BINDINGS)
    if user_bindings:
        for action, key in user_bindings.items():
            if action in merged:
                merged[action] = key
    return merged


def format_key_display(key: str) -> str:
    """Format a Textual canonical key name for human-readable display.

    Reverses alias normalization: ``slash`` -> ``/``,
    ``question_mark`` -> ``?``, etc. Modifier keys like ``ctrl+e``
    become ``Ctrl+E``.
    """
    if key in _DISPLAY_MAP:
        return _DISPLAY_MAP[key]
    if "+" in key:
        parts = key.split("+")
        return "+".join(p.capitalize() for p in parts)
    return key
