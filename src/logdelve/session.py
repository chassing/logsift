"""Session save/load for filter configurations."""

from __future__ import annotations

import re
import tomllib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import tomli_w

from logdelve.config import get_sessions_dir
from logdelve.models import (
    FilterRule,
    SearchDirection,
    SearchHistoryEntry,
    SearchPattern,
    SearchQuery,
    Session,
)

if TYPE_CHECKING:
    from pathlib import Path


def _search_pattern_to_dict(pattern: SearchPattern) -> dict[str, Any]:
    """Serialize a SearchPattern to a dict for TOML storage."""
    return {
        "pattern": pattern.query.pattern,
        "case_sensitive": pattern.query.case_sensitive,
        "is_regex": pattern.query.is_regex,
        "nav_enabled": pattern.nav_enabled,
    }


def _dict_to_search_pattern(d: dict[str, Any], color_index: int) -> SearchPattern | None:
    """Deserialize a dict to SearchPattern, returning None if invalid regex."""
    if d.get("is_regex"):
        try:
            re.compile(d["pattern"])
        except re.error:
            return None
    query = SearchQuery(
        pattern=d["pattern"],
        case_sensitive=d.get("case_sensitive", False),
        is_regex=d.get("is_regex", False),
        direction=SearchDirection.FORWARD,
    )
    return SearchPattern(
        query=query,
        color_index=color_index,
        nav_enabled=d.get("nav_enabled", True),
    )


def _history_entry_to_dict(entry: SearchHistoryEntry) -> dict[str, Any]:
    """Serialize a SearchHistoryEntry to a dict for TOML storage."""
    return {
        "pattern": entry.pattern,
        "case_sensitive": entry.case_sensitive,
        "is_regex": entry.is_regex,
    }


def _dict_to_history_entry(d: dict[str, Any]) -> SearchHistoryEntry:
    """Deserialize a dict to SearchHistoryEntry."""
    return SearchHistoryEntry(
        pattern=d["pattern"],
        case_sensitive=d.get("case_sensitive", False),
        is_regex=d.get("is_regex", False),
    )


def save_session(session: Session) -> Path:
    """Save a session to a TOML file. Returns the file path."""
    sessions_dir = get_sessions_dir()
    path = sessions_dir / f"{session.name}.toml"

    data: dict[str, Any] = {
        "version": session.version,
        "name": session.name,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "filters": [_filter_to_dict(f) for f in session.filters],
        "source_files": session.source_files,
        "bookmarks": {str(k): v for k, v in session.bookmarks.items()},
        "search_patterns": [_search_pattern_to_dict(p) for p in session.search_patterns],
        "search_history": [_history_entry_to_dict(e) for e in session.search_history],
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

    # Deserialize bookmarks (keys are strings in TOML, convert to int)
    raw_bookmarks = data.get("bookmarks", {})
    bookmarks = {int(k): v for k, v in raw_bookmarks.items()}

    # Deserialize search patterns with sequential color assignment
    version = data.get("version", 0)
    raw_patterns = data.get("search_patterns", [])
    search_patterns: list[SearchPattern] = []
    color_idx = 0
    for sp in raw_patterns:
        pattern = _dict_to_search_pattern(sp, color_index=color_idx)
        if pattern is not None:
            search_patterns.append(pattern)
            color_idx += 1

    # Deserialize search history
    search_history = [_dict_to_history_entry(h) for h in data.get("search_history", [])]

    return Session(
        name=data["name"],
        filters=filters,
        bookmarks=bookmarks,
        source_files=data.get("source_files", []),
        search_patterns=search_patterns,
        search_history=search_history,
        version=max(version, 1),
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


def rename_session(old_name: str, new_name: str) -> None:
    """Rename a saved session."""
    sessions_dir = get_sessions_dir()
    old_path = sessions_dir / f"{old_name}.toml"
    if old_path.exists():
        session = load_session(old_name)
        session = Session(
            name=new_name,
            filters=session.filters,
            bookmarks=session.bookmarks,
            source_files=session.source_files,
            search_patterns=session.search_patterns,
            search_history=session.search_history,
            version=session.version,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        save_session(session)
        old_path.unlink()


def create_session(
    name: str,
    filters: list[FilterRule],
    *,
    search_patterns: list[SearchPattern] | None = None,
    search_history: list[SearchHistoryEntry] | None = None,
) -> Session:
    """Create a new Session with current timestamp."""
    now = datetime.now(tz=UTC)
    return Session(
        name=name,
        filters=filters,
        search_patterns=search_patterns or [],
        search_history=search_history or [],
        created_at=now,
        updated_at=now,
    )


def _filter_to_dict(rule: FilterRule) -> dict[str, Any]:
    d: dict[str, Any] = {
        "filter_type": rule.filter_type.value,
        "pattern": rule.pattern,
        "enabled": rule.enabled,
        "is_regex": rule.is_regex,
        "case_sensitive": rule.case_sensitive,
        "is_json_key": rule.is_json_key,
        "is_component": rule.is_component,
        "is_time_range": rule.is_time_range,
    }
    if rule.json_key is not None:
        d["json_key"] = rule.json_key
    if rule.json_value is not None:
        d["json_value"] = rule.json_value
    if rule.component_name is not None:
        d["component_name"] = rule.component_name
    if rule.time_start is not None:
        d["time_start"] = rule.time_start
    if rule.time_end is not None:
        d["time_end"] = rule.time_end
    return d


def _dict_to_filter(d: dict[str, Any]) -> FilterRule:
    return FilterRule(
        filter_type=d["filter_type"],
        pattern=d.get("pattern", ""),
        enabled=d.get("enabled", True),
        is_regex=d.get("is_regex", False),
        case_sensitive=d.get("case_sensitive", False),
        is_json_key=d.get("is_json_key", False),
        json_key=d.get("json_key"),
        json_value=d.get("json_value"),
        is_component=d.get("is_component", False),
        component_name=d.get("component_name"),
        is_time_range=d.get("is_time_range", False),
        time_start=d.get("time_start"),
        time_end=d.get("time_end"),
    )
