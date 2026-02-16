"""Filter engine for log lines."""

from __future__ import annotations

from typing import Any

from logdelve.models import FilterRule, FilterType, LogLine


def apply_filters(lines: list[LogLine], rules: list[FilterRule]) -> list[int]:
    """Apply filter rules to log lines, returning indices of matching lines.

    Include filters use OR logic (match any include).
    Exclude filters use AND logic (excluded if matches any exclude).
    No include filters means all lines are candidates.
    """
    active_includes = [r for r in rules if r.enabled and r.filter_type == FilterType.INCLUDE]
    active_excludes = [r for r in rules if r.enabled and r.filter_type == FilterType.EXCLUDE]

    if not active_includes and not active_excludes:
        return list(range(len(lines)))

    result: list[int] = []
    for i, line in enumerate(lines):
        if active_includes and not any(_matches(line, r) for r in active_includes):
            continue

        if any(_matches(line, r) for r in active_excludes):
            continue

        result.append(i)

    return result


def check_line(line: LogLine, rules: list[FilterRule]) -> bool:
    """Check if a single line passes the current filter rules."""
    active_includes = [r for r in rules if r.enabled and r.filter_type == FilterType.INCLUDE]
    active_excludes = [r for r in rules if r.enabled and r.filter_type == FilterType.EXCLUDE]

    if not active_includes and not active_excludes:
        return True

    if active_includes and not any(_matches(line, r) for r in active_includes):
        return False

    return not any(_matches(line, r) for r in active_excludes)


def _matches(line: LogLine, rule: FilterRule) -> bool:
    """Check if a line matches a filter rule."""
    if rule.is_json_key:
        return _matches_json_key(line, rule)
    return rule.pattern.lower() in line.raw.lower()


def _matches_json_key(line: LogLine, rule: FilterRule) -> bool:
    """Check if a line's JSON content matches a key-value filter."""
    if line.parsed_json is None or rule.json_key is None:
        return False
    value = get_nested_value(line.parsed_json, rule.json_key)
    if value is None:
        return False
    return str(value) == rule.json_value


def get_nested_value(data: dict[str, Any], key_path: str) -> Any:
    """Get a value from nested dicts using dot-separated key path."""
    keys = key_path.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def flatten_json(data: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Flatten a JSON dict into (key_path, value_str) pairs."""
    result: list[tuple[str, str]] = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.extend(flatten_json(value, full_key))
        elif isinstance(value, list):
            result.append((full_key, str(value)))
        else:
            result.append((full_key, str(value)))
    return result
