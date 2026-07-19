"""Anonymous, opt-out usage telemetry.

One minimal event is sent per command (or MCP tool call) to measure
whether Queria actually gets used: the command name, whether it
succeeded, the frontend (cli / mcp), the package version and the target
dataset. SQL text, file paths and personal data are never sent.
See https://docs.queria.io/telemetry for details.

Opt out with any of:

- ``DO_NOT_TRACK=1`` (https://consoledonottrack.com)
- ``QUERIA_NO_TELEMETRY=1``
- ``queria telemetry disable`` (persists ``telemetry = false`` in the
  config file)

Events go to Queria's first-party endpoint (``telemetry.queria.io``),
which validates them against an allowlist before storing; no analytics
vendor credentials ship in this client. The client id is a random UUID
stored in the config file. When an API token is configured it is sent as
the Authorization header so the server can attribute usage to the
account; the client never handles the account id itself. Sending is
fail-silent and must never slow down or break a command.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request
import uuid

from queria import auth

DEFAULT_ENDPOINT = "https://telemetry.queria.io"

_TIMEOUT_SECONDS = 2.0

NOTICE = (
    "queria collects anonymous usage data (command name and version; never "
    "SQL text) to improve the tool. Opt out with `queria telemetry disable` "
    "or DO_NOT_TRACK=1. Details: https://docs.queria.io/telemetry"
)

# Environment variables that identify well-known agent runtimes. Used only
# to tell agent-driven usage apart from a human at a terminal.
_AGENT_ENV_VARS = {
    "CLAUDECODE": "claude-code",
    "CODEX_SANDBOX": "codex",
}


def _endpoint() -> str:
    """Ingest endpoint; the override exists for tests and staging."""
    return os.environ.get("QUERIA_TELEMETRY_URL", DEFAULT_ENDPOINT)


def enabled() -> bool:
    """Whether telemetry may be sent (not opted out)."""
    if os.environ.get("DO_NOT_TRACK") or os.environ.get("QUERIA_NO_TELEMETRY"):
        return False
    return auth.read_config().get("telemetry", True) is not False


def disable() -> None:
    """Persist the opt-out in the config file."""
    config = auth.read_config()
    config["telemetry"] = False
    auth._write_config(config)


def enable() -> None:
    """Remove a persisted opt-out."""
    config = auth.read_config()
    config.pop("telemetry", None)
    auth._write_config(config)


def _client_id() -> str:
    """Stable anonymous id, generated once and stored in the config file."""
    config = auth.read_config()
    client_id = config.get("telemetry_id")
    if isinstance(client_id, str) and client_id:
        return client_id
    client_id = uuid.uuid4().hex
    config["telemetry_id"] = client_id
    try:
        auth._write_config(config)
    except OSError:
        pass
    return client_id


def show_notice_once() -> None:
    """Print the first-run notice to stderr (once, tracked in the config)."""
    if not enabled():
        return
    config = auth.read_config()
    if config.get("telemetry_notice_shown") is True:
        return
    config["telemetry_notice_shown"] = True
    try:
        auth._write_config(config)
    except OSError:
        return
    print(NOTICE, file=sys.stderr)


def agent_context() -> str:
    """Name of the agent runtime driving this process, or ``""``."""
    for var, name in _AGENT_ENV_VARS.items():
        if os.environ.get(var):
            return name
    return ""


def track_command(
    command: str,
    *,
    frontend: str,
    version: str,
    success: bool,
    dataset: str = "",
) -> threading.Thread | None:
    """Send one ``cli_command`` event in a background thread.

    The thread is non-daemon so a short-lived CLI process waits for the
    request (bounded by the 2 s timeout) instead of dropping it at exit.
    Returns the thread for tests; ``None`` when telemetry is disabled.
    """
    if not enabled():
        return None

    payload = {
        "client_id": _client_id(),
        "events": [
            {
                "name": "cli_command",
                "params": {
                    "command": command,
                    "frontend": frontend,
                    "app_version": version,
                    "success": "true" if success else "false",
                    "dataset": dataset,
                    "agent": agent_context(),
                },
            }
        ],
    }
    # The server resolves the token's owner; the client never sees the
    # account id.
    token, _ = auth.resolve_token()

    thread = threading.Thread(target=_post, args=(payload, token))
    thread.start()
    return thread


def _post(payload: dict, token: str | None) -> None:
    try:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            _endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS).close()
    except Exception:  # noqa: BLE001 -- telemetry must never break a command
        pass
