"""Anonymous, opt-out usage telemetry.

One minimal event is sent per command (or MCP tool call) to measure
whether Queria actually gets used: the command name, whether it
succeeded, the frontend (cli / mcp / python), the package version and the
target dataset. SQL text, file paths and personal data are never sent.
See https://docs.queria.io/telemetry for details.

Opt out with any of:

- ``DO_NOT_TRACK=1`` (https://consoledonottrack.com)
- ``QUERIA_NO_TELEMETRY=1``
- ``queria telemetry disable`` (persists ``telemetry = false`` in the
  config file)

Events go to Google Analytics 4 via the Measurement Protocol. The client
id is a random UUID stored in the config file; when an API token has been
saved with ``queria auth set-token``, the token's owner (resolved once via
the data.queria.io ``/whoami`` endpoint) is attached as the user id so CLI
usage can be joined with web activity. Sending is fail-silent and must
never slow down or break a command.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
import uuid

from queria import auth

# GA4 Measurement Protocol credentials. The api_secret is not a secret in
# the usual sense (it only allows writing events) and shipping it in the
# client is the standard Measurement Protocol setup. Telemetry is disabled
# entirely while these are unset. The environment variables exist for
# testing and staging.
DEFAULT_MEASUREMENT_ID = ""
DEFAULT_API_SECRET = ""
DEFAULT_ENDPOINT = "https://www.google-analytics.com/mp/collect"

_TIMEOUT_SECONDS = 2.0


def _measurement_id() -> str:
    return os.environ.get("QUERIA_TELEMETRY_MEASUREMENT_ID", DEFAULT_MEASUREMENT_ID)


def _api_secret() -> str:
    return os.environ.get("QUERIA_TELEMETRY_API_SECRET", DEFAULT_API_SECRET)


def _endpoint() -> str:
    return os.environ.get("QUERIA_TELEMETRY_URL", DEFAULT_ENDPOINT)

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


def enabled() -> bool:
    """Whether telemetry may be sent (credentials present and not opted out)."""
    if not _measurement_id() or not _api_secret():
        return False
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


def resolve_user_id(storage: str, token: str) -> str | None:
    """Resolve the token's owner via ``GET {storage}/whoami`` and cache it.

    Returns the user id, or ``None`` when resolution fails (telemetry then
    stays anonymous). Never raises.
    """
    try:
        request = urllib.request.Request(
            f"{storage}/whoami", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as res:
            user_id = json.loads(res.read().decode("utf-8")).get("user_id")
    except (OSError, ValueError, urllib.error.URLError):
        return None
    if not isinstance(user_id, str) or not user_id:
        return None
    config = auth.read_config()
    config["telemetry_user_id"] = user_id
    try:
        auth._write_config(config)
    except OSError:
        pass
    return user_id


def clear_user_id() -> None:
    """Drop the cached user id (called when the token is removed)."""
    config = auth.read_config()
    if config.pop("telemetry_user_id", None) is not None:
        auth._write_config(config)


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
    user_id = auth.read_config().get("telemetry_user_id")
    if isinstance(user_id, str) and user_id:
        payload["user_id"] = user_id

    thread = threading.Thread(target=_post, args=(payload,))
    thread.start()
    return thread


def _post(payload: dict) -> None:
    try:
        request = urllib.request.Request(
            f"{_endpoint()}?measurement_id={_measurement_id()}&api_secret={_api_secret()}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS).close()
    except Exception:  # noqa: BLE001 -- telemetry must never break a command
        pass
