"""Pydantic models for logdelve."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic needs this at runtime for model field resolution
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, PrivateAttr, computed_field


class ContentType(StrEnum):
    """Type of content in a log line."""

    JSON = "json"
    TEXT = "text"


class LogLevel(StrEnum):
    """Log severity level."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class LogLine(BaseModel):
    """A single parsed log line."""

    line_number: int
    raw: str
    timestamp: datetime | None = None
    content_type: ContentType
    content_offset: int = 0
    parsed_json: dict[str, Any] | None = None
    log_level: LogLevel | None = None
    component: str | None = None
    source_line_number: int | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content(self) -> str:
        """Content portion of the line (raw without timestamp prefix)."""
        return self.raw[self.content_offset :]


class FilterType(StrEnum):
    """Type of filter rule."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


class FilterRule(BaseModel):
    """A single filter rule."""

    filter_type: FilterType
    pattern: str
    enabled: bool = True
    is_regex: bool = False
    case_sensitive: bool = False
    is_json_key: bool = False
    json_key: str | None = None
    json_value: str | None = None
    is_component: bool = False
    component_name: str | None = None
    is_time_range: bool = False
    time_start: str | None = None
    time_end: str | None = None


class SearchDirection(StrEnum):
    """Direction for text search."""

    FORWARD = "forward"
    BACKWARD = "backward"


class SearchQuery(BaseModel):
    """A search query with options."""

    pattern: str
    case_sensitive: bool = False
    is_regex: bool = False
    direction: SearchDirection = SearchDirection.FORWARD


_MAX_SEARCH_PATTERNS = 10


class SearchPattern(BaseModel):
    """A single search pattern with its assigned color."""

    query: SearchQuery
    color_index: int


class SearchPatternSet(BaseModel):
    """An ordered set of active search patterns (max 10) with sequential color assignment."""

    patterns: list[SearchPattern] = []
    _next_color: int = PrivateAttr(default=0)

    def add(self, query: SearchQuery) -> SearchPattern | None:
        """Add a pattern with the next available color index.

        Returns the new SearchPattern, or None if at capacity (10).
        """
        if len(self.patterns) >= _MAX_SEARCH_PATTERNS:
            return None

        used_indices = {p.color_index for p in self.patterns}
        # Find next available color starting from _next_color
        color_index = self._next_color
        for _ in range(_MAX_SEARCH_PATTERNS):
            if color_index not in used_indices:
                break
            color_index = (color_index + 1) % _MAX_SEARCH_PATTERNS
        else:
            return None  # All colors taken (shouldn't happen if len < 10)

        pattern = SearchPattern(query=query, color_index=color_index)
        self.patterns.append(pattern)
        self._next_color = (color_index + 1) % _MAX_SEARCH_PATTERNS
        return pattern

    def remove_last(self) -> SearchPattern | None:
        """Pop the last pattern (stack-style). Returns removed pattern or None if empty."""
        if not self.patterns:
            return None
        return self.patterns.pop()

    def clear(self) -> None:
        """Remove all patterns."""
        self.patterns.clear()
        self._next_color = 0

    @property
    def active_count(self) -> int:
        """Number of active patterns."""
        return len(self.patterns)

    @property
    def is_empty(self) -> bool:
        """Whether the pattern set is empty."""
        return len(self.patterns) == 0


class AppConfig(BaseModel):
    """Application configuration persisted to disk."""

    theme: str = "textual-dark"


class Session(BaseModel):
    """A named set of filter rules and bookmarks."""

    name: str
    filters: list[FilterRule] = []
    bookmarks: dict[int, str] = {}
    source_files: list[str] = []
    created_at: datetime
    updated_at: datetime
