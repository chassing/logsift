"""AWS CloudWatch Logs operations via boto3."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_logs import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import FilteredLogEventTypeDef


def create_client(
    region: str | None = None,
    profile: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    session_token: str | None = None,
    endpoint_url: str | None = None,
) -> CloudWatchLogsClient:
    """Create a boto3 CloudWatch Logs client."""
    try:
        import boto3
    except ImportError:
        print("Error: boto3 not installed. Run: pip install logsift[aws]", file=sys.stderr)
        sys.exit(1)

    session = boto3.Session(
        profile_name=profile,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
    )
    return session.client("logs", endpoint_url=endpoint_url)


def _ts_to_ms(dt: datetime) -> int:
    """Convert datetime to epoch milliseconds."""
    return int(dt.timestamp() * 1000)


def _ms_to_iso(ms: int) -> str:
    """Convert epoch milliseconds to ISO 8601 string."""
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()


def _extract_message(raw_message: str, message_key: str | None) -> str:
    """Extract a nested message from a JSON log line.

    If message_key is set, tries to parse raw_message as JSON and extract that key.
    Falls back to the raw message if parsing fails or key is absent.
    """
    if not message_key:
        return raw_message

    import json

    try:
        parsed = json.loads(raw_message)
    except (json.JSONDecodeError, ValueError):
        return raw_message

    if isinstance(parsed, dict) and message_key in parsed:
        return str(parsed[message_key])
    return raw_message


def _format_event(event: FilteredLogEventTypeDef, message_key: str | None = None) -> tuple[str, str]:
    """Format a single CloudWatch log event as (iso_timestamp, message)."""
    ts = _ms_to_iso(event.get("timestamp", 0))
    raw_msg = event.get("message", "").rstrip("\n")
    msg = _extract_message(raw_msg, message_key)
    return ts, msg


def get_log_events(
    client: CloudWatchLogsClient,
    log_group: str,
    stream_prefix: str,
    start: datetime,
    end: datetime,
    message_key: str | None = None,
) -> Iterator[tuple[str, str]]:
    """Download log events, yield (iso_timestamp, message) tuples."""
    paginator = client.get_paginator("filter_log_events")
    paginate_kwargs = {
        "logGroupName": log_group,
        "startTime": _ts_to_ms(start),
        "endTime": _ts_to_ms(end),
        "interleaved": True,
    }
    if stream_prefix:
        paginate_kwargs["logStreamNamePrefix"] = stream_prefix

    for page in paginator.paginate(**paginate_kwargs):  # type: ignore[arg-type]
        for event in page.get("events", []):
            yield _format_event(event, message_key)


def tail_log_events(
    client: CloudWatchLogsClient,
    log_group: str,
    stream_prefix: str,
    start: datetime,
    poll_interval: float = 2.0,
    message_key: str | None = None,
) -> None:
    """Poll for new log events and write to stdout. Runs until KeyboardInterrupt."""
    start_time = _ts_to_ms(start)
    seen_ids: set[str] = set()

    while True:
        try:
            if stream_prefix:
                response = client.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_time,
                    interleaved=True,
                    logStreamNamePrefix=stream_prefix,
                )
            else:
                response = client.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_time,
                    interleaved=True,
                )
        except KeyboardInterrupt:
            break

        for event in response.get("events", []):
            event_id = event.get("eventId", "")
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            ts, msg = _format_event(event, message_key)
            print(f"{ts} {msg}", flush=True)

        next_token = response.get("nextToken")
        if next_token:
            start_time = 0  # nextToken handles positioning
        else:
            try:
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                break

        # Limit memory for seen IDs
        if len(seen_ids) > 10000:
            seen_ids = set(list(seen_ids)[-5000:])


def list_log_groups(client: CloudWatchLogsClient, prefix: str | None = None) -> Iterator[str]:
    """List CloudWatch log groups, yielding names as they arrive."""
    paginator = client.get_paginator("describe_log_groups")
    paginate_kwargs = {}
    if prefix:
        paginate_kwargs["logGroupNamePrefix"] = prefix

    for page in paginator.paginate(**paginate_kwargs):  # type: ignore[arg-type]
        for group in page.get("logGroups", []):
            yield group["logGroupName"]


def list_log_streams(client: CloudWatchLogsClient, log_group: str, prefix: str | None = None) -> Iterator[str]:
    """List CloudWatch log streams, yielding names as they arrive."""
    paginator = client.get_paginator("describe_log_streams")
    paginate_kwargs: dict[str, str] = {"logGroupName": log_group}
    if prefix:
        paginate_kwargs["logStreamNamePrefix"] = prefix

    for page in paginator.paginate(**paginate_kwargs):  # type: ignore[arg-type]
        for stream in page.get("logStreams", []):
            yield stream["logStreamName"]
