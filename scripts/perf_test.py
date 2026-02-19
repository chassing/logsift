"""Performance benchmark for logdelve core engines.

Usage:
    uv run python scripts/perf_test.py
"""

# ruff: noqa: PLR2004, T201
from __future__ import annotations

import time
from typing import Any

from logdelve.filters import apply_filters
from logdelve.models import FilterRule, FilterType, LogLine, SearchDirection, SearchQuery
from logdelve.parsers.auto import AutoParser
from logdelve.search import find_matches

# --- Log line templates ---

JSON_TEMPLATES = [
    '2024-01-15T10:30:{sec:02d}Z {{"log_level": "info", "message": "Request processed", "duration_ms": {n}, "user": "admin"}}',
    '2024-01-15T10:30:{sec:02d}Z {{"log_level": "error", "message": "Connection failed", "code": {n}, "retry": true}}',
    '2024-01-15T10:30:{sec:02d}Z {{"log_level": "warn", "message": "Slow query", "table": "users", "elapsed": {n}}}',
]

TEXT_TEMPLATES = [
    "2024-01-15T10:30:{sec:02d}Z Connection established from 192.168.1.{n}",
    "Jan 15 10:30:{sec:02d} myhost syslogd: message {n}",
    "2024-01-15T10:30:{sec:02d}Z Health check passed (attempt {n})",
]
parser = AutoParser()


def generate_lines(count: int) -> list[str]:
    """Generate a mix of JSON and text log lines."""
    templates = JSON_TEMPLATES + TEXT_TEMPLATES
    result: list[str] = []
    for i in range(count):
        tmpl = templates[i % len(templates)]
        raw = tmpl.format(sec=i % 60, n=i)
        result.append(raw)
    return result


def bench_filter(lines: list[LogLine]) -> float:
    """Benchmark apply_filters with 3 active filter rules."""
    rules = [
        FilterRule(filter_type=FilterType.INCLUDE, pattern="info"),
        FilterRule(filter_type=FilterType.EXCLUDE, pattern="health check"),
        FilterRule(filter_type=FilterType.INCLUDE, pattern="error", is_regex=True),
    ]
    start = time.perf_counter()
    apply_filters(lines, rules)
    return time.perf_counter() - start


def bench_search(lines: list[LogLine]) -> float:
    """Benchmark find_matches with a text pattern."""
    query = SearchQuery(pattern="connection", case_sensitive=False, direction=SearchDirection.FORWARD)
    start = time.perf_counter()
    find_matches(lines, query)
    return time.perf_counter() - start


def bench_search_regex(lines: list[LogLine]) -> float:
    """Benchmark find_matches with a regex pattern."""
    query = SearchQuery(
        pattern=r"duration_ms.*\d{3}", is_regex=True, case_sensitive=False, direction=SearchDirection.FORWARD
    )
    start = time.perf_counter()
    find_matches(lines, query)
    return time.perf_counter() - start


def format_rate(count: int, elapsed: float) -> str:
    """Format lines/sec."""
    if elapsed <= 0:
        return "inf"
    rate = count / elapsed
    if rate >= 1_000_000:
        return f"{rate / 1_000_000:.1f}M/s"
    if rate >= 1_000:
        return f"{rate / 1_000:.1f}K/s"
    return f"{rate:.0f}/s"


def run_benchmark(count: int) -> dict[str, Any]:
    """Run all benchmarks for a given line count."""
    raw_lines = generate_lines(count)

    # Parse
    parse_start = time.perf_counter()
    lines = [parser.parse_line(i + 1, raw) for i, raw in enumerate(raw_lines)]
    parse_time = time.perf_counter() - parse_start

    # Filter
    filter_time = bench_filter(lines)

    # Search - text
    search_time = bench_search(lines)

    # Search - regex
    search_regex_time = bench_search_regex(lines)

    return {
        "count": count,
        "parse": parse_time,
        "filter": filter_time,
        "search": search_time,
        "search_regex": search_regex_time,
    }


def main() -> None:
    sizes = [10_000, 100_000, 500_000]

    print(f"{'Lines':>10}  {'Parse':>10}  {'Filter':>10}  {'Search':>10}  {'Regex':>10}")
    print("-" * 58)

    for size in sizes:
        result = run_benchmark(size)
        count = result["count"]
        print(
            f"{count:>10,}  "
            f"{result['parse']:>7.3f}s {format_rate(count, result['parse']):>5}  "
            f"{result['filter']:>7.3f}s {format_rate(count, result['filter']):>5}  "
            f"{result['search']:>7.3f}s {format_rate(count, result['search']):>5}  "
            f"{result['search_regex']:>7.3f}s {format_rate(count, result['search_regex']):>5}"
        )

    print()
    print("Done.")


if __name__ == "__main__":
    main()
