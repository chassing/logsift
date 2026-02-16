"""CloudWatch subcommands for logdelve."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

import typer

from logdelve.aws import (
    create_client,
    get_log_events,
    list_log_groups,
    list_log_streams,
    tail_log_events,
)
from logdelve.utils import parse_time

if TYPE_CHECKING:
    from mypy_boto3_logs import CloudWatchLogsClient

cw_app = typer.Typer(name="cloudwatch", help="AWS CloudWatch log operations")

# Type aliases for AWS credential options
_AccessKey = Annotated[
    str | None, typer.Option("--aws-access-key-id", help="AWS access key ID", envvar="AWS_ACCESS_KEY_ID")
]
_SecretKey = Annotated[
    str | None, typer.Option("--aws-secret-access-key", help="AWS secret access key", envvar="AWS_SECRET_ACCESS_KEY")
]
_SessionToken = Annotated[
    str | None, typer.Option("--aws-session-token", help="AWS session token", envvar="AWS_SESSION_TOKEN")
]
_Profile = Annotated[str | None, typer.Option("--profile", help="AWS profile", envvar="AWS_PROFILE")]
_Region = Annotated[str | None, typer.Option("--aws-region", help="AWS region", envvar="AWS_DEFAULT_REGION")]
_EndpointUrl = Annotated[
    str | None, typer.Option("--aws-endpoint-url", help="AWS endpoint URL", envvar="AWS_ENDPOINT_URL")
]


def _client(
    access_key: str | None,
    secret_key: str | None,
    session_token: str | None,
    profile: str | None,
    region: str | None,
    endpoint_url: str | None,
) -> CloudWatchLogsClient:
    return create_client(
        region=region,
        profile=profile,
        access_key=access_key,
        secret_key=secret_key,
        session_token=session_token,
        endpoint_url=endpoint_url,
    )


@cw_app.command("get")
def get_logs(
    log_group: Annotated[str, typer.Argument(help="CloudWatch log group name")],
    stream_prefix: Annotated[str, typer.Argument(help="Log stream name prefix")] = "",
    start: Annotated[str, typer.Option("--start", "-s", help="Start time in UTC (5m, 1h, 2days, or ISO 8601)")] = "5m",
    end: Annotated[str | None, typer.Option("--end", "-e", help="End time in UTC (default: now)")] = None,
    tail: Annotated[bool, typer.Option("--tail", help="Keep polling for new events")] = False,
    message_key: Annotated[
        str | None, typer.Option("--message-key", "-m", help="Extract nested JSON key from message (default: message)")
    ] = "message",
    aws_access_key_id: _AccessKey = None,
    aws_secret_access_key: _SecretKey = None,
    aws_session_token: _SessionToken = None,
    profile: _Profile = None,
    aws_region: _Region = None,
    aws_endpoint_url: _EndpointUrl = None,
) -> None:
    """Download CloudWatch log events to stdout."""
    client = _client(aws_access_key_id, aws_secret_access_key, aws_session_token, profile, aws_region, aws_endpoint_url)

    start_time = parse_time(start)
    end_time = parse_time(end) if end else datetime.now(tz=UTC)

    events = get_log_events(client, log_group, stream_prefix, start_time, end_time, message_key=message_key)
    for ts, msg, stream in events:
        print(f"[{stream}] {ts} {msg}", flush=tail)

    if tail:
        tail_log_events(client, log_group, stream_prefix, end_time, message_key=message_key)


@cw_app.command("groups")
def groups(
    log_group_prefix: Annotated[str | None, typer.Argument(help="Log group name prefix")] = None,
    aws_access_key_id: _AccessKey = None,
    aws_secret_access_key: _SecretKey = None,
    aws_session_token: _SessionToken = None,
    profile: _Profile = None,
    aws_region: _Region = None,
    aws_endpoint_url: _EndpointUrl = None,
) -> None:
    """List CloudWatch log groups."""
    client = _client(aws_access_key_id, aws_secret_access_key, aws_session_token, profile, aws_region, aws_endpoint_url)
    for name in list_log_groups(client, prefix=log_group_prefix):
        print(name)


@cw_app.command("streams")
def streams(
    log_group: Annotated[str, typer.Argument(help="CloudWatch log group name")],
    prefix: Annotated[str | None, typer.Argument(help="Stream name prefix")] = None,
    aws_access_key_id: _AccessKey = None,
    aws_secret_access_key: _SecretKey = None,
    aws_session_token: _SessionToken = None,
    profile: _Profile = None,
    aws_region: _Region = None,
    aws_endpoint_url: _EndpointUrl = None,
) -> None:
    """List CloudWatch log streams."""
    client = _client(aws_access_key_id, aws_secret_access_key, aws_session_token, profile, aws_region, aws_endpoint_url)
    for name in list_log_streams(client, log_group, prefix=prefix):
        print(name)
