"""Generate deterministic demo log files for promotional VHS recordings.

Modes:
    incident      - Multi-service cascading DB failure (~400 lines) -> /tmp/incident.log
    baseline      - Clean baseline from yesterday (~300 lines) -> /tmp/baseline.log
    current-slow  - Today's logs with slow queries and new errors (~300 lines) -> /tmp/current.log

Usage:
    python scripts/gen_promo_logs.py incident
    python scripts/gen_promo_logs.py baseline
    python scripts/gen_promo_logs.py current-slow
"""

# ruff: noqa: S311, PLR2004, PLR0914, T201, S108
from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Components
API = "api-server-7db64-a1b2c3"
WORKER = "order-processor-85bc6-d4e5f6"
CACHE = "cache-redis-4f2a1-g7h8i9"

COMPONENTS = [API, WORKER, CACHE]

PATHS = [
    "/api/v1/users",
    "/api/v1/orders",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/products",
]


def gen_line(ts: datetime, component: str, level: str, event: str, **extra: object) -> str:
    """Generate a single log line in CloudWatch bracket-prefix format."""
    data: dict[str, object] = {"level": level, "event": event, "timestamp": ts.isoformat(), **extra}
    return f"[{component}] {ts.isoformat()} {json.dumps(data)}"


def make_request_id(n: int) -> str:
    """Generate a deterministic request ID from a sequence number."""
    return f"req-{n:04d}-a1b2-3c4d-e5f6-{n * 7:012x}"


def gen_incident(base: datetime) -> list[str]:
    """Generate multi-service cascading DB failure for Topic 1 & 3.

    Story arc:
    - Phase 1 (lines 0-199): Normal traffic, healthy system
    - Phase 2 (lines 200-249): First signs - slow queries, pool warnings
    - Phase 3 (lines 250-349): Cascading failure - ECONNREFUSED, 500s, timeouts
    - Phase 4 (lines 350-399): Continued errors with recovery attempts
    """
    random.seed(42)
    lines: list[str] = []
    req_counter = 0

    for i in range(400):
        ts = base + timedelta(seconds=i * 2.5 + random.uniform(0, 0.5))

        if i < 200:
            # Phase 1: Normal traffic
            lines.extend(_normal_request_cycle(ts, i, req_counter))
            req_counter += 1

        elif i < 250:
            # Phase 2: First signs of trouble
            if i % 8 == 0:
                # Slow query warnings from worker
                dur = random.randint(500, 2000)
                lines.append(
                    gen_line(
                        ts,
                        WORKER,
                        "warn",
                        "Slow query detected: SELECT * FROM orders WHERE status='pending'",
                        duration_ms=dur,
                        query_id=f"q-{i}",
                    )
                )
            elif i % 12 == 0:
                # Connection pool warnings from API
                pool_active = random.randint(45, 50)
                lines.append(
                    gen_line(
                        ts,
                        API,
                        "warn",
                        "Database connection pool running low",
                        pool_active=pool_active,
                        pool_max=50,
                    )
                )
            else:
                lines.extend(_normal_request_cycle(ts, i, req_counter))
                req_counter += 1

        elif i < 350:
            # Phase 3: Cascading failure - full request lifecycles ending in errors
            lines.extend(_failing_request_cycle(ts, i, req_counter))
            req_counter += 1

        else:
            # Phase 4: Continued errors with some recovery attempts
            if i % 4 == 0:
                # Recovery attempt (no request lifecycle)
                lines.append(
                    gen_line(
                        ts,
                        API,
                        "info",
                        "Attempting database reconnection",
                        attempt=random.randint(1, 5),
                        pool_id="primary",
                    )
                )
            elif i % 4 == 2:
                # Memory pressure warning (no request lifecycle)
                mem_pct = random.randint(88, 97)
                lines.append(
                    gen_line(
                        ts,
                        random.choice([API, WORKER]),
                        "warn",
                        "Memory usage critical",
                        memory_pct=mem_pct,
                        threshold=85,
                    )
                )
            else:
                # Failing request lifecycle
                lines.extend(_failing_request_cycle(ts, i, req_counter))
            req_counter += 1

    # Sort by timestamp to ensure chronological order
    lines.sort(key=lambda line: line.split("] ", 1)[1].split(" ", 1)[0])
    return lines


def _normal_request_cycle(base_ts: datetime, idx: int, req_num: int) -> list[str]:
    """Generate a normal request lifecycle across components."""
    lines: list[str] = []
    req_id = make_request_id(req_num)
    path = PATHS[idx % len(PATHS)]
    dur = random.randint(20, 80)

    # API receives request
    lines.append(
        gen_line(
            base_ts,
            API,
            "info",
            f"Received GET {path}",
            http_path=path,
            request_id=req_id,
        )
    )

    # Cache lookup
    cache_ts = base_ts + timedelta(milliseconds=random.randint(1, 5))
    key = f"cache:{path.split('/')[-1]}:{random.randint(1, 50)}"
    hit = random.random() > 0.3
    lines.append(
        gen_line(
            cache_ts,
            CACHE,
            "debug",
            f"Cache {'hit' if hit else 'miss'} for key {key}",
            cache_key=key,
            request_id=req_id,
        )
    )

    # Worker processing (for order/product paths)
    if "orders" in path or "products" in path:
        worker_ts = base_ts + timedelta(milliseconds=random.randint(5, 30))
        lines.append(
            gen_line(
                worker_ts,
                WORKER,
                "info",
                f"Processing request for {path}",
                http_path=path,
                request_id=req_id,
            )
        )

    # API completes request
    done_ts = base_ts + timedelta(milliseconds=dur)
    lines.append(
        gen_line(
            done_ts,
            API,
            "info",
            f"Completed GET {path}",
            http_path=path,
            http_status=200,
            duration_ms=dur,
            request_id=req_id,
        )
    )

    # Periodic health checks
    if idx % 15 == 0:
        hc_ts = base_ts + timedelta(milliseconds=random.randint(100, 500))
        lines.append(gen_line(hc_ts, API, "info", "Health check passed"))

    return lines


def _failing_request_cycle(base_ts: datetime, idx: int, req_num: int) -> list[str]:
    """Generate a request lifecycle that ends with an error.

    Same structure as _normal_request_cycle (API received -> Cache -> Worker)
    but the final step is an error instead of a successful completion.
    This ensures the request_id appears across multiple components.
    """
    lines: list[str] = []
    req_id = make_request_id(req_num)
    path = PATHS[idx % len(PATHS)]

    # API receives request (same as normal)
    lines.append(
        gen_line(
            base_ts,
            API,
            "info",
            f"Received GET {path}",
            http_path=path,
            request_id=req_id,
        )
    )

    # Cache lookup (same as normal)
    cache_ts = base_ts + timedelta(milliseconds=random.randint(1, 5))
    key = f"cache:{path.split('/')[-1]}:{random.randint(1, 50)}"
    lines.append(
        gen_line(
            cache_ts,
            CACHE,
            "debug",
            f"Cache miss for key {key}",
            cache_key=key,
            request_id=req_id,
        )
    )

    # Worker tries to process (same as normal)
    worker_ts = base_ts + timedelta(milliseconds=random.randint(5, 30))
    lines.append(
        gen_line(
            worker_ts,
            WORKER,
            "info",
            f"Processing request for {path}",
            http_path=path,
            request_id=req_id,
        )
    )

    # Error: one of several failure modes
    error_ts = base_ts + timedelta(milliseconds=random.randint(50, 500))
    failure_type = idx % 3
    if failure_type == 0:
        # DB connection refused
        host = f"10.0.1.{random.randint(1, 3)}"
        lines.append(
            gen_line(
                error_ts,
                WORKER,
                "error",
                f"Connection refused to {host}:5432",
                error_code="ECONNREFUSED",
                request_id=req_id,
                retry=random.randint(1, 3),
            )
        )
        # API gets the failure response
        api_err_ts = error_ts + timedelta(milliseconds=random.randint(5, 20))
        lines.append(
            gen_line(
                api_err_ts,
                API,
                "error",
                f"Request failed: GET {path}",
                http_path=path,
                http_status=500,
                duration_ms=random.randint(500, 5000),
                request_id=req_id,
            )
        )
    elif failure_type == 1:
        # Timeout
        dur = random.randint(5000, 30000)
        lines.append(
            gen_line(
                error_ts,
                API,
                "error",
                f"Timeout after {dur}ms on {path}",
                http_path=path,
                http_status=504,
                duration_ms=dur,
                request_id=req_id,
            )
        )
    else:
        # Worker job failure
        job_type = random.choice(["process_order", "send_notification", "update_inventory"])
        lines.append(
            gen_line(
                error_ts,
                WORKER,
                "error",
                f"Job failed: {job_type}",
                job_type=job_type,
                request_id=req_id,
                error="database connection timeout after 30s",
            )
        )
        api_err_ts = error_ts + timedelta(milliseconds=random.randint(5, 20))
        lines.append(
            gen_line(
                api_err_ts,
                API,
                "error",
                f"Request failed: GET {path}",
                http_path=path,
                http_status=500,
                duration_ms=random.randint(500, 5000),
                request_id=req_id,
            )
        )

    return lines


def gen_baseline(base: datetime) -> list[str]:
    """Generate clean baseline logs for Topic 2.

    Normal operations: all 200s, fast response times, standard patterns.
    """
    random.seed(100)
    lines: list[str] = []
    req_counter = 0

    normal_events = [
        ("Received GET {path}", "info", API),
        ("Completed GET {path}", "info", API),
        ("Cache hit for key {key}", "debug", CACHE),
        ("Processing request for {path}", "info", WORKER),
        ("Health check passed", "info", API),
        ("Request processed", "info", API),
    ]

    for i in range(300):
        ts = base + timedelta(seconds=i * 3 + random.uniform(0, 1))
        path = PATHS[i % len(PATHS)]
        key = f"user:{random.randint(1, 50)}"
        req_id = make_request_id(req_counter)

        if i % 5 == 0:
            req_counter += 1
            req_id = make_request_id(req_counter)

        evt_template, level, comp = random.choice(normal_events)
        event = evt_template.format(path=path, key=key)
        extra: dict[str, object] = {"http_path": path, "request_id": req_id}

        if "Completed" in event:
            extra["http_status"] = 200
            extra["duration_ms"] = random.randint(20, 80)
        if "Health" in event:
            extra = {}

        lines.append(gen_line(ts, comp, level, event, **extra))

    return lines


def gen_current_slow(base: datetime) -> list[str]:
    """Generate today's problematic logs for Topic 2.

    Same normal patterns as baseline but with novel error patterns:
    - Slow query detected (novel template)
    - Connection pool exhausted (novel template)
    - Memory usage critical (novel template)
    - Request processed with much higher duration_ms (frequency spike)
    """
    random.seed(200)
    lines: list[str] = []
    req_counter = 0

    normal_events = [
        ("Received GET {path}", "info", API),
        ("Completed GET {path}", "info", API),
        ("Cache hit for key {key}", "debug", CACHE),
        ("Processing request for {path}", "info", WORKER),
        ("Health check passed", "info", API),
        ("Request processed", "info", API),
    ]

    for i in range(300):
        ts = base + timedelta(seconds=i * 3 + random.uniform(0, 1))
        path = PATHS[i % len(PATHS)]
        key = f"user:{random.randint(1, 50)}"
        req_id = make_request_id(req_counter)

        if i % 5 == 0:
            req_counter += 1
            req_id = make_request_id(req_counter)

        # Novel patterns start appearing after line 100
        if i > 100 and i % 10 == 0:
            # Novel: slow query
            table = random.choice(["orders", "users", "products", "inventory"])
            dur = random.randint(1500, 8000)
            lines.append(
                gen_line(
                    ts,
                    WORKER,
                    "warn",
                    f"Slow query detected: SELECT * FROM {table}",  # noqa: S608
                    duration_ms=dur,
                    query_id=f"q-{i}",
                    table=table,
                )
            )
            continue

        if i > 150 and i % 15 == 0:
            # Novel: connection pool exhausted
            pool_active = 50
            lines.append(
                gen_line(
                    ts,
                    API,
                    "error",
                    "Connection pool exhausted, all connections in use",
                    pool_active=pool_active,
                    pool_max=50,
                    waiting_requests=random.randint(5, 20),
                )
            )
            continue

        if i > 200 and i % 20 == 0:
            # Novel: memory critical
            mem_pct = random.randint(90, 98)
            lines.append(
                gen_line(
                    ts,
                    random.choice([API, WORKER]),
                    "warn",
                    "Memory usage critical",
                    memory_pct=mem_pct,
                    threshold=85,
                )
            )
            continue

        # Normal events, but with degraded performance after line 100
        evt_template, level, comp = random.choice(normal_events)
        event = evt_template.format(path=path, key=key)
        extra: dict[str, object] = {"http_path": path, "request_id": req_id}

        if "Completed" in event:
            if i > 100:
                # Frequency spike: much higher duration
                extra["duration_ms"] = random.randint(200, 3000)
                extra["http_status"] = 200 if random.random() > 0.15 else 500
            else:
                extra["duration_ms"] = random.randint(20, 80)
                extra["http_status"] = 200
        if "Health" in event:
            extra = {}

        lines.append(gen_line(ts, comp, level, event, **extra))

    return lines


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <incident|baseline|current-slow>", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]

    # Fixed timestamps for reproducible demo recordings
    incident_base = datetime(2026, 2, 18, 14, 0, 0, tzinfo=UTC)
    baseline_base = datetime(2026, 2, 17, 8, 0, 0, tzinfo=UTC)
    current_base = datetime(2026, 2, 18, 8, 0, 0, tzinfo=UTC)

    generators: dict[str, tuple[datetime, Path]] = {
        "incident": (incident_base, Path("/tmp/incident.log")),
        "baseline": (baseline_base, Path("/tmp/baseline.log")),
        "current-slow": (current_base, Path("/tmp/current.log")),
    }

    if mode not in generators:
        print(f"Unknown mode: {mode}. Use: {', '.join(generators)}", file=sys.stderr)
        sys.exit(1)

    base_time, output_path = generators[mode]

    if mode == "incident":
        lines = gen_incident(base_time)
    elif mode == "baseline":
        lines = gen_baseline(base_time)
    else:
        lines = gen_current_slow(base_time)

    output_path.write_text("\n".join(lines) + "\n")
    print(f"{output_path} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
