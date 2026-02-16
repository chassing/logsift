"""Pydantic models for logdelve."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ContentType(StrEnum):
    """Type of content in a log line."""

    JSON = "json"
    TEXT = "text"


class LogLine(BaseModel):
    """A single parsed log line."""

    line_number: int
    raw: str
    timestamp: datetime | None = None
    content_type: ContentType
    content: str
    parsed_json: dict[str, Any] | None = None


class FilterType(StrEnum):
    """Type of filter rule."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


class FilterRule(BaseModel):
    """A single filter rule."""

    filter_type: FilterType
    pattern: str
    enabled: bool = True
    is_json_key: bool = False
    json_key: str | None = None
    json_value: str | None = None


class Session(BaseModel):
    """A named set of filter rules."""

    name: str
    filters: list[FilterRule] = []
    created_at: datetime
    updated_at: datetime
