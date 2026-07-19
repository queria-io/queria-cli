"""Telemetry: opt-out resolution, payload shape and fail-silence.

Events are asserted against a real local HTTP server instead of mocking
urllib, so the tests exercise the actual sending path.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from queria import auth, cli, telemetry
from queria.auth import tomllib  # tomli fallback on Python 3.10


@pytest.fixture()
def capture_server():
    """Local stand-in for telemetry.queria.io capturing POSTed events."""
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 -- http.server API
            length = int(self.headers.get("Content-Length", 0))
            received.append(
                {
                    "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                    "user_agent": self.headers.get("User-Agent"),
                    "body": json.loads(self.rfile.read(length)),
                }
            )
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", received
    server.shutdown()


@pytest.fixture()
def telemetry_env(monkeypatch: pytest.MonkeyPatch, capture_server):
    """Point telemetry at the capture server and lift the suite-wide opt-out."""
    url, received = capture_server
    monkeypatch.setenv("QUERIA_TELEMETRY_URL", url)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("QUERIA_NO_TELEMETRY", raising=False)
    return url, received


def _wait_for(received: list, count: int = 1, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while len(received) < count and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(received) >= count


def test_enabled_by_default(telemetry_env) -> None:
    assert telemetry.enabled() is True


def test_env_opt_outs(monkeypatch: pytest.MonkeyPatch, telemetry_env) -> None:
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert telemetry.enabled() is False
    monkeypatch.delenv("DO_NOT_TRACK")
    monkeypatch.setenv("QUERIA_NO_TELEMETRY", "1")
    assert telemetry.enabled() is False


def test_disable_enable_roundtrip(telemetry_env) -> None:
    telemetry.disable()
    assert telemetry.enabled() is False
    with open(auth.config_path(), "rb") as f:
        assert tomllib.load(f)["telemetry"] is False
    telemetry.enable()
    assert telemetry.enabled() is True


def test_track_command_disabled_returns_none(telemetry_env) -> None:
    telemetry.disable()
    assert telemetry.track_command("list", frontend="cli", version="0", success=True) is None


def test_track_command_sends_payload(telemetry_env) -> None:
    _url, received = telemetry_env
    thread = telemetry.track_command(
        "sql", frontend="cli", version="0.4.0", success=True, dataset="zipcode"
    )
    thread.join(timeout=5)
    _wait_for(received)
    event = received[0]
    assert event["path"] == "/"
    assert event["authorization"] is None
    # urllib's default UA is classified as a bot by Cloudflare (403)
    assert event["user_agent"] == "queria-cli/0.4.0"
    body = event["body"]
    assert body["events"] == [
        {
            "name": "cli_command",
            "params": {
                "command": "sql",
                "frontend": "cli",
                "app_version": "0.4.0",
                "success": "true",
                "dataset": "zipcode",
                "agent": telemetry.agent_context(),
            },
        }
    ]

    # The anonymous id is generated once and reused.
    telemetry.track_command("list", frontend="cli", version="0.4.0", success=False).join(timeout=5)
    _wait_for(received, count=2)
    assert received[1]["body"]["client_id"] == body["client_id"]


def test_token_is_sent_as_bearer_header(telemetry_env) -> None:
    _url, received = telemetry_env
    auth.set_token("qk_telemetry_test")
    telemetry.track_command("list", frontend="cli", version="0", success=True).join(timeout=5)
    _wait_for(received)
    assert received[0]["authorization"] == "Bearer qk_telemetry_test"
    # user_id はサーバー側で解決するため、クライアントのペイロードには含まれない
    assert "user_id" not in received[0]["body"]


def test_send_fail_silent(monkeypatch: pytest.MonkeyPatch, telemetry_env) -> None:
    monkeypatch.setenv("QUERIA_TELEMETRY_URL", "http://127.0.0.1:1")
    thread = telemetry.track_command("list", frontend="cli", version="0", success=True)
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_show_notice_once(telemetry_env, capsys: pytest.CaptureFixture) -> None:
    telemetry.show_notice_once()
    assert "telemetry" in capsys.readouterr().err
    telemetry.show_notice_once()
    assert capsys.readouterr().err == ""


def test_notice_suppressed_when_disabled(
    monkeypatch: pytest.MonkeyPatch, telemetry_env, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    telemetry.show_notice_once()
    assert capsys.readouterr().err == ""


def test_agent_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.delenv("CODEX_SANDBOX", raising=False)
    assert telemetry.agent_context() == ""
    monkeypatch.setenv("CLAUDECODE", "1")
    assert telemetry.agent_context() == "claude-code"


def test_cli_command_is_tracked(telemetry_env, storage: str) -> None:
    _url, received = telemetry_env
    cli.main(["--storage-url", storage, "list"])
    _wait_for(received)
    params = received[0]["body"]["events"][0]["params"]
    assert params["command"] == "list"
    assert params["frontend"] == "cli"
    assert params["success"] == "true"


def test_cli_telemetry_subcommand(telemetry_env, capsys: pytest.CaptureFixture) -> None:
    cli.main(["telemetry", "disable"])
    assert telemetry.enabled() is False
    cli.main(["telemetry", "status"])
    assert "disabled" in capsys.readouterr().out
    cli.main(["telemetry", "enable"])
    assert telemetry.enabled() is True
