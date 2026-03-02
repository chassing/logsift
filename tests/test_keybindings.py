"""Tests for the keybindings module."""

from __future__ import annotations

import tomllib

from logdelve.keybindings import (
    DEFAULT_BINDINGS,
    build_keymap,
    generate_defaults_toml,
    get_merged_bindings,
    normalize_key,
    normalize_keybindings,
    validate_keybindings,
)

# --- normalize_key ---


def test_normalize_slash() -> None:
    assert normalize_key("/") == "slash"


def test_normalize_question_mark() -> None:
    assert normalize_key("?") == "question_mark"


def test_normalize_hash() -> None:
    assert normalize_key("#") == "hash"


def test_normalize_exclamation() -> None:
    assert normalize_key("!") == "exclamation_mark"


def test_normalize_at() -> None:
    assert normalize_key("@") == "at"


def test_normalize_colon() -> None:
    assert normalize_key(":") == "colon"


def test_normalize_left_bracket() -> None:
    assert normalize_key("[") == "left_square_bracket"


def test_normalize_right_bracket() -> None:
    assert normalize_key("]") == "right_square_bracket"


def test_normalize_already_canonical() -> None:
    assert normalize_key("slash") == "slash"
    assert normalize_key("ctrl+f") == "ctrl+f"
    assert normalize_key("f") == "f"


def test_normalize_unknown_symbol() -> None:
    assert normalize_key("z") == "z"
    assert normalize_key("ctrl+x") == "ctrl+x"


# --- normalize_keybindings ---


def test_normalize_dict_with_aliases() -> None:
    raw = {"search_forward": "/", "search_backward": "?", "toggle_line_numbers": "#"}
    result = normalize_keybindings(raw)
    assert result == {
        "search_forward": "slash",
        "search_backward": "question_mark",
        "toggle_line_numbers": "hash",
    }


def test_normalize_dict_already_canonical() -> None:
    raw = {"search_forward": "slash", "filter_in": "f"}
    result = normalize_keybindings(raw)
    assert result == {"search_forward": "slash", "filter_in": "f"}


# --- validate_keybindings ---


def test_valid_empty_dict() -> None:
    errors = validate_keybindings({})
    assert errors == []


def test_valid_single_override() -> None:
    # Remap search_forward to a key not used by any default
    errors = validate_keybindings({"search_forward": "ctrl+f"})
    assert errors == []


def test_unknown_action() -> None:
    errors = validate_keybindings({"nonexistent_action": "f"})
    assert len(errors) == 1
    assert "Unknown action" in errors[0]
    assert "nonexistent_action" in errors[0]


def test_non_snake_case_action() -> None:
    errors = validate_keybindings({"Search_Forward": "f"})
    assert len(errors) >= 1
    assert any("snake_case" in e for e in errors)


def test_protected_key_tab() -> None:
    errors = validate_keybindings({"search_forward": "tab"})
    assert len(errors) >= 1
    assert any("protected" in e.lower() for e in errors)


def test_protected_key_escape() -> None:
    errors = validate_keybindings({"search_forward": "escape"})
    assert len(errors) >= 1
    assert any("protected" in e.lower() for e in errors)


def test_protected_key_ctrl_c() -> None:
    errors = validate_keybindings({"search_forward": "ctrl+c"})
    assert len(errors) >= 1
    assert any("protected" in e.lower() for e in errors)


def test_protected_key_ctrl_q() -> None:
    errors = validate_keybindings({"search_forward": "ctrl+q"})
    assert len(errors) >= 1
    assert any("protected" in e.lower() for e in errors)


def test_invalid_key_format_dash() -> None:
    errors = validate_keybindings({"search_forward": "ctrl-f"})
    assert len(errors) >= 1
    assert any("Invalid key format" in e for e in errors)


def test_invalid_key_format_space() -> None:
    errors = validate_keybindings({"search_forward": "ctrl f"})
    assert len(errors) >= 1
    assert any("Invalid key format" in e for e in errors)


def test_invalid_key_format_empty() -> None:
    errors = validate_keybindings({"search_forward": ""})
    assert len(errors) >= 1
    assert any("Invalid key format" in e for e in errors)


def test_duplicate_keys_in_user_config() -> None:
    errors = validate_keybindings({"search_forward": "f", "search_backward": "f"})
    assert len(errors) >= 1
    assert any("Duplicate key" in e for e in errors)
    assert any("f" in e for e in errors)


def test_cross_conflict_with_default() -> None:
    # Remap search_forward to "q" which is default for quit
    errors = validate_keybindings({"search_forward": "q"})
    assert len(errors) >= 1
    assert any("conflicts" in e.lower() or "duplicate" in e.lower() for e in errors)


def test_multiple_errors_collected() -> None:
    errors = validate_keybindings(
        {
            "nonexistent_action": "f",
            "search_forward": "tab",
            "filter_in": "ctrl-x",
        }
    )
    assert len(errors) >= 3


def test_valid_complex_override() -> None:
    # Swap two keys: search_forward gets filter_in's key and vice versa
    errors = validate_keybindings({"search_forward": "f", "filter_in": "slash"})
    assert errors == []


# --- build_keymap ---


def test_build_keymap_empty_overrides() -> None:
    result = build_keymap({})
    assert result == {}


def test_build_keymap_single_override() -> None:
    result = build_keymap({"search_forward": "ctrl+f"})
    assert result == {"search_forward": "ctrl+f"}


def test_build_keymap_multiple_overrides() -> None:
    result = build_keymap({"search_forward": "ctrl+f", "filter_in": "i"})
    assert result == {"search_forward": "ctrl+f", "filter_in": "i"}


# --- generate_defaults_toml ---


def test_defaults_starts_with_header() -> None:
    result = generate_defaults_toml()
    assert result.startswith("[keybindings]")


def test_defaults_contains_all_actions() -> None:
    result = generate_defaults_toml()
    for action in DEFAULT_BINDINGS:
        assert action in result, f"Missing action: {action}"


def test_defaults_sorted_alphabetically() -> None:
    result = generate_defaults_toml()
    lines = [line for line in result.strip().split("\n") if "=" in line]
    action_names = [line.split("=")[0].strip() for line in lines]
    assert action_names == sorted(action_names)


def test_defaults_valid_toml() -> None:
    result = generate_defaults_toml()
    data = tomllib.loads(result)
    assert "keybindings" in data
    assert len(data["keybindings"]) == len(DEFAULT_BINDINGS)


# --- get_merged_bindings ---


def test_merged_no_overrides() -> None:
    result = get_merged_bindings()
    assert result == DEFAULT_BINDINGS
    # Must be a copy, not the original
    assert result is not DEFAULT_BINDINGS


def test_merged_with_overrides() -> None:
    result = get_merged_bindings({"search_forward": "ctrl+f"})
    assert result["search_forward"] == "ctrl+f"
    # Other keys unchanged
    assert result["filter_in"] == DEFAULT_BINDINGS["filter_in"]


# --- DEFAULT_BINDINGS registry ---


def test_registry_has_app_level_actions() -> None:
    """Registry must include app-level actions from app.py BINDINGS."""
    app_actions = [
        "manage_sessions",
        "toggle_all_filters",
        "search_forward",
        "search_backward",
        "filter_in",
        "filter_out",
        "analyze",
        "manage_filters",
        "toggle_theme",
        "cycle_level_filter",
        "toggle_anomalies",
        "quit",
        "toggle_tail_pause",
        "show_help",
        "clear_lines",
        "save_screenshot_svg",
    ]
    for action in app_actions:
        assert action in DEFAULT_BINDINGS, f"Missing app action: {action}"


def test_registry_has_log_view_actions() -> None:
    """Registry must include log_view-level actions."""
    lv_actions = [
        "cursor_up",
        "cursor_down",
        "page_up",
        "page_down",
        "scroll_home",
        "scroll_end",
        "goto_top",
        "scroll_bottom",
        "toggle_json_global",
        "toggle_json_line",
        "toggle_line_numbers",
        "cycle_component_display",
        "next_match",
        "prev_match",
    ]
    for action in lv_actions:
        assert action in DEFAULT_BINDINGS, f"Missing log_view action: {action}"


def test_registry_excludes_non_configurable() -> None:
    """Registry must NOT include internal or positional bindings."""
    assert "next_demo_label" not in DEFAULT_BINDINGS
    # toggle_filter(1) through toggle_filter(9) should not appear
    for i in range(1, 10):
        assert f"toggle_filter({i})" not in DEFAULT_BINDINGS
        assert f"toggle_filter_{i}" not in DEFAULT_BINDINGS
