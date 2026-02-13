"""Filter engine for log lines."""

from __future__ import annotations

from logsift.models import FilterRule, FilterType, LogLine


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
        text = line.raw.lower()

        if active_includes and not any(r.pattern.lower() in text for r in active_includes):
            continue

        if any(r.pattern.lower() in text for r in active_excludes):
            continue

        result.append(i)

    return result
