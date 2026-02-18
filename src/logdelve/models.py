"""Pydantic models for logdelve."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic needs this at runtime for model field resolution
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, computed_field


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


class AppConfig(BaseModel):
    """Application configuration persisted to disk."""

    theme: str = "textual-dark"


class Session(BaseModel):
    """A named set of filter rules."""

    name: str
    filters: list[FilterRule] = []
    created_at: datetime
    updated_at: datetime
