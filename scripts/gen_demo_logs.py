"""Generate realistic demo log files for VHS recordings."""

# ruff: noqa: S311, PLR2004, PLR0914, T201
from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime, timedelta


def gen_line(ts: datetime, component: str, level: str, event: str, **extra: object) -> str:
    data: dict[str, object] = {"level": level, "event": event, "timestamp": ts.isoformat(), **extra}
    return f"[{component}] {ts.isoformat()} {json.dumps(data)}"


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "current"
    now = datetime.now(tz=UTC)
    base = now - timedelta(hours=1)
    lines: list[str] = []

    components = ["api-server-7db64-abc12", "api-worker-85bc6-xyz34", "redis-cache-4f2a1-def56"]
    paths = ["/api/v1/users", "/api/v1/orders", "/api/v1/health", "/api/v1/auth/login", "/api/v1/products"]
    events_normal = [
        ("Start GET {path}", "info"),
        ("Done GET {path}", "info"),
        ("Cache hit for key {key}", "debug"),
        ("Health check passed", "info"),
        ("Request processed", "info"),
    ]
    request_id = ""

    for i in range(500):
        ts = base + timedelta(seconds=i * 2 + random.uniform(0, 1))
        comp = random.choice(components)
        path = random.choice(paths)
        key = f"user:{random.randint(1, 100)}"

        # keep request_id for 5 lines to simulate related events, then generate a new one
        if i % 5 == 0:
            request_id = (
                f"{random.randint(10000000, 99999999):08x}-abcd-1234-efgh-{random.randint(10000000, 99999999):08x}"
            )

        if mode == "baseline":
            # Baseline: only normal events
            evt_template, level = random.choice(events_normal)
            event = evt_template.format(path=path, key=key)
            extra: dict[str, object] = {"http_path": path, "request_id": request_id}
            if "Done" in event:
                extra["http_status"] = 200
                extra["duration_seconds"] = round(random.uniform(0.01, 0.5), 3)
            lines.append(gen_line(ts, comp, level, event, **extra))
        # Current: mix of normal + anomalies
        elif i > 200 and random.random() < 0.15:
            # Anomaly: connection errors (new pattern)
            event = f"Connection refused to 10.0.{random.randint(1, 5)}.{random.randint(1, 254)}:5432"
            lines.append(gen_line(ts, comp, "error", event, error_code="ECONNREFUSED", retry=random.randint(1, 3)))
        elif i > 250 and random.random() < 0.1:
            # Anomaly: timeout (new pattern)
            event = f"Timeout after {random.randint(5000, 30000)}ms on {path}"
            lines.append(gen_line(ts, comp, "error", event, http_path=path, http_status=504))
        elif i > 300 and random.random() < 0.05:
            # Anomaly: OOM warning (new pattern)
            event = "Memory usage critical"
            lines.append(gen_line(ts, comp, "warn", event, memory_pct=random.randint(90, 99), threshold=85))
        else:
            evt_template, level = random.choice(events_normal)
            event = evt_template.format(path=path, key=key)
            extra = {"http_path": path, "request_id": request_id}
            if "Done" in event:
                extra["http_status"] = 200 if random.random() > 0.05 else 500
                extra["duration_seconds"] = round(random.uniform(0.01, 2.0 if i > 200 else 0.5), 3)
            lines.append(gen_line(ts, comp, level, event, **extra))

    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
