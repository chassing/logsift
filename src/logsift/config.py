"""XDG directory management for logsift."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir


def get_config_dir() -> Path:
    """Get the logsift config directory."""
    return Path(user_config_dir("logsift"))


def get_sessions_dir() -> Path:
    """Get the sessions directory, creating it if needed."""
    d = get_config_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d
