"""Pydantic models for logsift."""

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
