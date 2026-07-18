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
    """Local server capturing POSTed telemetry and answering /whoami GETs."""
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 -- http.server API
            length = int(self.headers.get("Content-Length", 0))
            received.append(
                {
                    "path": self.path,
                    "body": json.loads(self.rfile.read(length)),
                }
            )
            self.send_response(204)
            self.end_headers()

        def do_GET(self):  # noqa: N802 -- http.server API
            body = json.dumps({"user_id": "user-123", "key_id": "key-1"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", received
    server.shutdown()


@pytest.fixture()
def telemetry_env(monkeypatch: pytest.MonkeyPatch, capture_server):
    """Point telemetry at the capture server with credentials set."""
    url, received = capture_server
    monkeypatch.setenv("QUERIA_TELEMETRY_MEASUREMENT_ID", "G-TEST")
    monkeypatch.setenv("QUERIA_TELEMETRY_API_SECRET", "test-secret")
    monkeypatch.setenv("QUERIA_TELEMETRY_URL", f"{url}/mp/collect")
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("QUERIA_NO_TELEMETRY", raising=False)
    return url, received


def _wait_for(received: list, count: int = 1, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while len(received) < count and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(received) >= count


def test_disabled_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUERIA_TELEMETRY_MEASUREMENT_ID", raising=False)
    monkeypatch.delenv("QUERIA_TELEMETRY_API_SECRET", raising=False)
    assert telemetry.enabled() is (bool(telemetry.DEFAULT_MEASUREMENT_ID) and bool(telemetry.DEFAULT_API_SECRET))


def test_env_opt_outs(monkeypatch: pytest.MonkeyPatch, telemetry_env) -> None:
    assert telemetry.enabled() is True
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
        "sql", frontend="cli", version="0.2.1", success=True, dataset="zipcode"
    )
    thread.join(timeout=5)
    _wait_for(received)
    event = received[0]
    assert "measurement_id=G-TEST" in event["path"]
    body = event["body"]
    assert "user_id" not in body
    assert body["events"] == [
        {
            "name": "cli_command",
            "params": {
                "command": "sql",
                "frontend": "cli",
                "app_version": "0.2.1",
                "success": "true",
                "dataset": "zipcode",
                "agent": telemetry.agent_context(),
            },
        }
    ]

    # The anonymous id is generated once and reused.
    telemetry.track_command("list", frontend="cli", version="0.2.1", success=False).join(timeout=5)
    _wait_for(received, count=2)
    assert received[1]["body"]["client_id"] == body["client_id"]


def test_user_id_resolution_and_clear(telemetry_env) -> None:
    url, received = telemetry_env
    assert telemetry.resolve_user_id(url, "qk_test") == "user-123"
    telemetry.track_command("list", frontend="cli", version="0", success=True).join(timeout=5)
    _wait_for(received)
    assert received[0]["body"]["user_id"] == "user-123"

    telemetry.clear_user_id()
    assert "telemetry_user_id" not in auth.read_config()


def test_resolve_user_id_fail_silent(telemetry_env) -> None:
    assert telemetry.resolve_user_id("http://127.0.0.1:1", "qk_test") is None


def test_send_fail_silent(monkeypatch: pytest.MonkeyPatch, telemetry_env) -> None:
    monkeypatch.setenv("QUERIA_TELEMETRY_URL", "http://127.0.0.1:1/mp/collect")
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
