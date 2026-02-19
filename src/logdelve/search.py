"""Search engine for finding text matches in log lines."""

from __future__ import annotations

import operator
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logdelve.models import LogLine, SearchPatternSet, SearchQuery


def find_matches(lines: list[LogLine], query: SearchQuery) -> list[tuple[int, int, int]]:
    """Find all matches in log lines, returning (line_index, start, end) tuples."""
    results: list[tuple[int, int, int]] = []

    if query.is_regex:
        flags = 0 if query.case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query.pattern, flags)
        except re.error:
            return results
        for i, line in enumerate(lines):
            results.extend((i, m.start(), m.end()) for m in pattern.finditer(line.raw))
    else:
        text_pattern = query.pattern if query.case_sensitive else query.pattern.lower()
        pat_len = len(text_pattern)
        if pat_len == 0:
            return results
        for i, line in enumerate(lines):
            raw = line.raw if query.case_sensitive else line.raw.lower()
            start = 0
            while True:
                pos = raw.find(text_pattern, start)
                if pos == -1:
                    break
                results.append((i, pos, pos + pat_len))
                start = pos + 1

    return results


def find_all_pattern_matches(
    lines: list[LogLine],
    patterns: SearchPatternSet,
) -> list[tuple[int, int, int, int]]:
    """Find matches for all patterns, returning (line_index, start, end, pattern_index) tuples.

    The pattern_index is the position in patterns.patterns (not color_index).
    Results are sorted by (line_index, start) for correct rendering order.
    """
    results: list[tuple[int, int, int, int]] = []
    for pattern_index, pattern in enumerate(patterns.patterns):
        for line_idx, start, end in find_matches(lines, pattern.query):
            results.append((line_idx, start, end, pattern_index))
    results.sort(key=operator.itemgetter(0, 1))
    return results
