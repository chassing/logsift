"""Message template extraction and grouping for log analysis."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from logdelve.models import LogLevel, LogLine

# Tokenization patterns (order matters: more specific first)
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\w.+:-]*")
_IPV4_RE = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
_PATH_RE = re.compile(r"/[\w./-]+")
_HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
_NUM_RE = re.compile(r"-?\d+\.?\d*")
_QUOTED_RE = re.compile(r'"[^"]*"')


def extract_template(content: str, is_json: bool = False, parsed_json: dict[str, Any] | None = None) -> str:
    """Replace variable parts of a log message with tokens.

    For JSON lines with parsed data, uses key-structure-based templating.
    For text lines, uses regex-based tokenization.
    """
    if is_json and parsed_json is not None:
        # Group by event/message field, not full key structure
        for key in _EVENT_KEYS:
            if key in parsed_json and isinstance(parsed_json[key], str):
                return f"{key}:{_tokenize_text(parsed_json[key])}"
        # Fallback: full key structure for JSON without event field
        return _extract_json_template(parsed_json)
    return _tokenize_text(content)


def _tokenize_text(text: str) -> str:
    """Replace variable parts in text with tokens."""
    result = text
    result = _UUID_RE.sub("<UUID>", result)
    result = _ISO_TS_RE.sub("<TS>", result)
    result = _IPV4_RE.sub("<IP>", result)
    result = _PATH_RE.sub("<PATH>", result)
    result = _HEX_RE.sub("<HEX>", result)
    result = _NUM_RE.sub("<NUM>", result)
    return result


def _extract_json_template(data: dict[str, Any]) -> str:
    """Create a template from JSON by keeping keys and tokenizing values."""
    parts: list[str] = []
    for key, value in sorted(data.items()):
        if isinstance(value, dict):
            parts.append(f"{key}={{{_extract_json_template(value)}}}")
        elif isinstance(value, list):
            parts.append(f"{key}=[...]")
        elif isinstance(value, bool):
            parts.append(f"{key}=<BOOL>")
        elif isinstance(value, int | float):
            parts.append(f"{key}=<NUM>")
        elif isinstance(value, str):
            tokenized = _tokenize_text(value)
            if tokenized != value:
                parts.append(f"{key}={tokenized}")
            else:
                parts.append(f"{key}=<STR>")
        else:
            parts.append(f"{key}=<?>")
    return " ".join(parts)


# Fields commonly used as the "event identifier" in JSON logs
_EVENT_KEYS = ("event", "message", "msg", "error", "err", "description", "text", "action")


def _json_display(data: dict[str, Any]) -> str:
    """Create a compact human-readable display string for a JSON log line.

    Shows the event/message field as primary text, with key count as metadata.
    """
    # Find the identifying field
    event_text = None
    for key in _EVENT_KEYS:
        if key in data and isinstance(data[key], str):
            event_text = _tokenize_text(data[key])
            break

    if event_text:
        return event_text
    # Fallback: show first few key names
    keys = sorted(data.keys())[:5]
    suffix = f" +{len(data) - 5}" if len(data) > 5 else ""
    return f"{{{', '.join(keys)}{suffix}}}"


def _json_filter_pattern(data: dict[str, Any]) -> str:
    """Create a minimal filter pattern for a JSON log line.

    Uses the event/message field value (tokenized) for matching.
    Falls back to the first few key names if no event field found.
    """
    for key in _EVENT_KEYS:
        if key in data and isinstance(data[key], str):
            return _tokenize_text(data[key])
    # Fallback: use first recognizable string value
    for key in sorted(data.keys()):
        if isinstance(data[key], str) and len(data[key]) > 3:
            return _tokenize_text(data[key])
    return ""


def _compute_hash(template: str) -> str:
    """Compute a short hash for a template string."""
    return hashlib.sha256(template.encode()).hexdigest()[:16]


class MessageTemplate:
    """A group of log lines sharing the same message template."""

    def __init__(self, template: str, display: str, example: str, content_pattern: str) -> None:
        self.template = template
        self.template_hash = _compute_hash(template)
        self.display = display  # human-readable short label for the dialog
        self.example = example
        self.content_pattern = content_pattern  # tokenized text for regex filtering
        self.count = 1
        self.line_indices: list[int] = []
        self.log_level: LogLevel | None = None
        self.first_seen = 0
        self.last_seen = 0
        self._level_counts: dict[LogLevel, int] = {}

    def add_line(self, line_index: int, level: LogLevel | None) -> None:
        """Record a line matching this template."""
        self.line_indices.append(line_index)
        self.count = len(self.line_indices)
        self.last_seen = line_index
        if level is not None:
            self._level_counts[level] = self._level_counts.get(level, 0) + 1
            # Most frequent level
            self.log_level = max(self._level_counts, key=self._level_counts.get)  # type: ignore[arg-type]


def build_template_groups(lines: list[LogLine]) -> list[MessageTemplate]:
    """Group log lines by their message template.

    Returns templates sorted by count (descending).
    """
    from logdelve.models import ContentType

    groups: dict[str, MessageTemplate] = {}

    for i, line in enumerate(lines):
        is_json = line.content_type == ContentType.JSON
        template_str = extract_template(line.content, is_json=is_json, parsed_json=line.parsed_json)
        template_hash = _compute_hash(template_str)

        if template_hash not in groups:
            # display + filter_pattern: for JSON use event field, for text use tokenized content
            if is_json and line.parsed_json is not None:
                display = _json_display(line.parsed_json)
                filter_pattern = _json_filter_pattern(line.parsed_json)
            else:
                display = _tokenize_text(line.content)
                filter_pattern = _tokenize_text(line.content)
            groups[template_hash] = MessageTemplate(template_str, display, line.content, filter_pattern)
            groups[template_hash].first_seen = i

        groups[template_hash].add_line(i, line.log_level)

    return sorted(groups.values(), key=lambda t: t.count, reverse=True)


def template_to_regex(template: str) -> str:
    """Convert a template back to a regex pattern for filtering."""
    escaped = re.escape(template)
    escaped = escaped.replace(re.escape("<UUID>"), r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    escaped = escaped.replace(re.escape("<TS>"), r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[\w.+:-]*")
    escaped = escaped.replace(re.escape("<IP>"), r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
    escaped = escaped.replace(re.escape("<PATH>"), r"/[\w./-]+")
    escaped = escaped.replace(re.escape("<HEX>"), r"[0-9a-f]{8,}")
    escaped = escaped.replace(re.escape("<NUM>"), r"-?\d+\.?\d*")
    escaped = escaped.replace(re.escape("<STR>"), r".+?")
    escaped = escaped.replace(re.escape("<BOOL>"), r"(?:true|false)")
    return escaped


class FieldGroup:
    """A group of lines sharing the same value for a specific JSON field."""

    def __init__(self, key: str, value: str, display: str, *, is_json_filter: bool = True) -> None:
        self.key = key
        self.value = value
        self.display = display
        self.is_json_filter = is_json_filter  # False for synthetic groups like ">0"
        self.count = 0
        self.line_indices: list[int] = []

    def add_line(self, line_index: int) -> None:
        self.line_indices.append(line_index)
        self.count = len(self.line_indices)


# Keys to skip in field analysis (noise/boilerplate)
_SKIP_FIELD_KEYS = frozenset(
    {
        "timestamp",
        "time",
        "ts",
        "@timestamp",
        "request_id",
        "trace_id",
        "span_id",
        "level",
        "log_level",
        "severity",
        "loglevel",
        "lvl",
    }
)


def build_field_groups(lines: list[LogLine]) -> list[FieldGroup]:
    """Analyze JSON field values across all lines.

    - String/bool fields: group by exact value
    - Int fields: group as =0 vs >0 (zero/non-zero)
    - Float fields: skipped
    - High-cardinality string keys (>20 values): skipped
    """
    from logdelve.models import ContentType

    groups: dict[str, FieldGroup] = {}
    key_values: dict[str, set[str]] = {}
    # Track which keys are numeric for zero/non-zero grouping
    numeric_keys: set[str] = set()

    for i, line in enumerate(lines):
        if line.content_type != ContentType.JSON or line.parsed_json is None:
            continue
        for key, value in line.parsed_json.items():
            if key in _SKIP_FIELD_KEYS:
                continue
            if isinstance(value, float):
                continue
            if isinstance(value, str) and len(value) > 50:
                continue

            # Integer fields: group as =0 / >0
            if isinstance(value, int):
                numeric_keys.add(key)
                bucket = f"{key}=0" if value == 0 else f"{key}>0"
                if bucket not in groups:
                    display = f"{key}=0" if value == 0 else f"{key}>0"
                    groups[bucket] = FieldGroup(key, "0" if value == 0 else ">0", display, is_json_filter=value == 0)
                groups[bucket].add_line(i)
            else:
                # String/bool: exact value
                str_value = str(value)
                key_values.setdefault(key, set()).add(str_value)
                group_key = f"{key}={str_value}"
                if group_key not in groups:
                    groups[group_key] = FieldGroup(key, str_value, f"{key}={str_value}")
                groups[group_key].add_line(i)

    # Filter out high-cardinality string keys (>20 values)
    high_cardinality = {k for k, v in key_values.items() if len(v) > 20}
    all_groups = [g for g in groups.values() if g.key not in high_cardinality]

    # Filter out fields that appear in every line
    total_json = sum(1 for line in lines if line.content_type == ContentType.JSON)
    if total_json > 0:
        all_groups = [g for g in all_groups if g.count < total_json * 0.95]

    all_groups.sort(key=lambda g: (g.count, g.key))
    return all_groups
