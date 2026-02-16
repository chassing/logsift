"""Search engine for finding text matches in log lines."""

from __future__ import annotations

import re

from logdelve.models import LogLine, SearchQuery


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
            for m in pattern.finditer(line.raw):
                results.append((i, m.start(), m.end()))
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
