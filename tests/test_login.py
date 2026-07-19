from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from queria import auth, login
from queria.cli import main


class _ExchangeStub(BaseHTTPRequestHandler):
    """Stands in for the queria.io exchange endpoint."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self.server.received_codes.append(body.get("code"))
        status, payload = self.server.response
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


@pytest.fixture
def exchange_server(monkeypatch: pytest.MonkeyPatch):
    server = HTTPServer(("127.0.0.1", 0), _ExchangeStub)
    server.response = (200, {"token": "qk_testtoken123", "name": "CLI (test)"})
    server.received_codes = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv(
        login.ENV_LOGIN_URL, f"http://127.0.0.1:{server.server_address[1]}"
    )
    yield server
    server.shutdown()
    server.server_close()


def _fake_browser(query_overrides: dict[str, str] | None = None):
    """Return a webbrowser.open stand-in that hits the CLI callback URL."""

    def fake_open(url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query).items()}
        query = {"code": "browser-code-1234567890", "state": params.get("state", "")}
        query.update(query_overrides or {})
        callback = (
            f"http://127.0.0.1:{params['port']}/callback?"
            + urllib.parse.urlencode(query)
        )

        def visit() -> None:
            try:
                with urllib.request.urlopen(callback) as response:
                    response.read()
            except urllib.error.HTTPError:
                pass  # the CLI answers 400 on a state mismatch

        threading.Thread(target=visit, daemon=True).start()
        return True

    return fake_open


def test_login_browser_flow_saves_token(
    exchange_server, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(login.webbrowser, "open", _fake_browser())
    main(["login"])
    assert auth.resolve_token() == ("qk_testtoken123", "config")
    assert exchange_server.received_codes == ["browser-code-1234567890"]
    out = capsys.readouterr().out
    assert "Logged in" in out
    assert "90 days" in out


def test_login_rejects_state_mismatch(
    exchange_server, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        login.webbrowser, "open", _fake_browser({"state": "wrong-state"})
    )
    monkeypatch.setattr(login, "_TIMEOUT_S", 0.5)
    with pytest.raises(SystemExit, match="timed out"):
        main(["login"])
    assert auth.resolve_token() == (None, None)
    assert exchange_server.received_codes == []


def test_login_times_out_without_callback(
    exchange_server, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(login, "_TIMEOUT_S", 0.2)
    with pytest.raises(SystemExit, match="timed out"):
        main(["login"])
    assert auth.resolve_token() == (None, None)


def test_login_reports_exchange_error(
    exchange_server, monkeypatch: pytest.MonkeyPatch
) -> None:
    exchange_server.response = (400, {"error": "invalid_or_expired_code"})
    monkeypatch.setattr(login.webbrowser, "open", _fake_browser())
    with pytest.raises(SystemExit, match="invalid_or_expired_code"):
        main(["login"])
    assert auth.resolve_token() == (None, None)


def test_login_rejects_malformed_token(
    exchange_server, monkeypatch: pytest.MonkeyPatch
) -> None:
    exchange_server.response = (200, {"token": "bad'; DROP SECRET x; --"})
    monkeypatch.setattr(login.webbrowser, "open", _fake_browser())
    with pytest.raises(SystemExit, match="invalid token"):
        main(["login"])
    assert auth.resolve_token() == (None, None)


def test_login_no_browser_prompts_for_code(
    exchange_server, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(
        "builtins.input", lambda prompt="": "pasted-code-1234567890"
    )
    main(["login", "--no-browser"])
    assert auth.resolve_token() == ("qk_testtoken123", "config")
    assert exchange_server.received_codes == ["pasted-code-1234567890"]
    assert "/cli-auth?name=" in capsys.readouterr().out


def test_logout_removes_token(capsys) -> None:
    auth.set_token("qk_tok123")
    main(["logout"])
    assert auth.resolve_token() == (None, None)
    out = capsys.readouterr().out
    assert "Token removed" in out
    assert "profile/api-keys" in out


def test_logout_without_token(capsys) -> None:
    main(["logout"])
    assert "No token" in capsys.readouterr().out
