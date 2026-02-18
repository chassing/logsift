"""XDG directory management and configuration for logdelve."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir

from logdelve.models import AppConfig


def get_config_dir() -> Path:
    """Get the logdelve config directory.

    Respects LOGDELVE_CONFIG_DIR environment variable if set.
    """
    if override := os.environ.get("LOGDELVE_CONFIG_DIR"):
        return Path(override)
    return Path(user_config_dir("logdelve"))


def get_sessions_dir() -> Path:
    """Get the sessions directory, creating it if needed."""
    d = get_config_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config() -> AppConfig:
    """Load application config from disk, returning defaults if not found."""
    path = get_config_dir() / "config.toml"
    if not path.exists():
        return AppConfig()
    try:
        data: dict[str, Any] = tomllib.loads(path.read_text())
        return AppConfig(**data)
    except (OSError, ValueError, TypeError, KeyError):
        return AppConfig()


def save_config(config: AppConfig) -> None:
    """Save application config to disk."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.toml"
    path.write_bytes(tomli_w.dumps(config.model_dump()).encode())
