"""Session save/load for filter configurations."""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomli_w

from logsift.config import get_sessions_dir
from logsift.models import FilterRule, Session


def save_session(session: Session) -> Path:
    """Save a session to a TOML file. Returns the file path."""
    sessions_dir = get_sessions_dir()
    path = sessions_dir / f"{session.name}.toml"

    data: dict[str, Any] = {
        "name": session.name,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "filters": [_filter_to_dict(f) for f in session.filters],
    }

    path.write_bytes(tomli_w.dumps(data).encode())
    return path


def load_session(name: str) -> Session:
    """Load a session from a TOML file."""
    sessions_dir = get_sessions_dir()
    path = sessions_dir / f"{name}.toml"

    if not path.exists():
        msg = f"Session '{name}' not found"
        raise FileNotFoundError(msg)

    data = tomllib.loads(path.read_text())
    filters = [_dict_to_filter(f) for f in data.get("filters", [])]

    return Session(
        name=data["name"],
        filters=filters,
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def list_sessions() -> list[str]:
    """List all saved session names."""
    sessions_dir = get_sessions_dir()
    return sorted(p.stem for p in sessions_dir.glob("*.toml"))


def delete_session(name: str) -> None:
    """Delete a saved session."""
    sessions_dir = get_sessions_dir()
    path = sessions_dir / f"{name}.toml"
    if path.exists():
        path.unlink()


def create_session(name: str, filters: list[FilterRule]) -> Session:
    """Create a new Session with current timestamp."""
    now = datetime.now(tz=UTC)
    return Session(name=name, filters=filters, created_at=now, updated_at=now)


def _filter_to_dict(rule: FilterRule) -> dict[str, Any]:
    d: dict[str, Any] = {
        "filter_type": rule.filter_type.value,
        "pattern": rule.pattern,
        "enabled": rule.enabled,
        "is_json_key": rule.is_json_key,
    }
    if rule.json_key is not None:
        d["json_key"] = rule.json_key
    if rule.json_value is not None:
        d["json_value"] = rule.json_value
    return d


def _dict_to_filter(d: dict[str, Any]) -> FilterRule:
    return FilterRule(
        filter_type=d["filter_type"],
        pattern=d.get("pattern", ""),
        enabled=d.get("enabled", True),
        is_json_key=d.get("is_json_key", False),
        json_key=d.get("json_key"),
        json_value=d.get("json_value"),
    )
