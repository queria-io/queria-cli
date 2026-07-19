"""Browser-based login flow (``queria login``).

The CLI starts a loopback HTTP server, opens the queria.io approval page
in a browser, and receives a one-time code via a redirect to the loopback
port. The code is then exchanged over HTTPS for an API token, which is
stored in the config file. ``--no-browser`` skips the loopback server:
the approval page shows the code and the user pastes it into the CLI.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from queria import auth, core

DEFAULT_LOGIN_URL = "https://queria.io"
ENV_LOGIN_URL = "QUERIA_LOGIN_URL"

_TIMEOUT_S = 300
# Matches better-auth's maximumNameLength on the server.
_NAME_MAX = 32

_PAGE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>queria login</title></head>
<body style="font-family: system-ui, sans-serif; margin: 4rem auto; max-width: 32rem">
<h1 style="font-size: 1.25rem">{title}</h1><p>{body}</p>
</body></html>"""


def _page(title: str, body: str) -> bytes:
    return _PAGE_HTML.format(title=title, body=body).encode()


class _CallbackServer(HTTPServer):
    """Loopback server that captures the one-time code from the redirect."""

    def __init__(self, expected_state: str) -> None:
        super().__init__(("127.0.0.1", 0), _CallbackHandler)
        self.expected_state = expected_state
        self.code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackServer

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        url = urllib.parse.urlsplit(self.path)
        if url.path != "/callback":
            self._respond(404, _page("Not found", "This page does not exist."))
            return
        params = urllib.parse.parse_qs(url.query)
        code = (params.get("code") or [""])[0]
        state = (params.get("state") or [""])[0]
        if not code or not secrets.compare_digest(state, self.server.expected_state):
            self._respond(
                400,
                _page(
                    "Login failed",
                    "The request did not come from this CLI session. "
                    "Close this tab and run <code>queria login</code> again.",
                ),
            )
            return
        self.server.code = code
        self._respond(
            200,
            _page(
                "Login complete",
                "You are logged in. Close this tab and return to the terminal.",
            ),
        )

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # keep the terminal quiet


def _wait_for_code(server: _CallbackServer, timeout_s: float) -> str | None:
    deadline = time.monotonic() + timeout_s
    while server.code is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        server.timeout = remaining
        server.handle_request()
    return server.code


def _key_name() -> str:
    return f"CLI ({socket.gethostname()})"[:_NAME_MAX]


def _exchange(login_url: str, code: str) -> str:
    """Exchange the one-time code for an API token."""
    request = urllib.request.Request(
        f"{login_url}/api/cli-auth/exchange",
        data=json.dumps({"code": code}).encode(),
        headers={
            "Content-Type": "application/json",
            # Self-identify (and avoid bot heuristics on the default urllib UA).
            "User-Agent": f"queria-cli/{core.version()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error = json.load(exc).get("error", "")
        except (json.JSONDecodeError, OSError):
            error = ""
        detail = error or f"HTTP {exc.code}"
        raise RuntimeError(
            f"login failed: {detail}. Run `queria login` again."
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"login failed: could not reach {login_url} ({exc})") from exc
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("login failed: the server returned no token")
    return token


def run(no_browser: bool = False) -> None:
    """Run the interactive login flow and save the resulting token."""
    login_url = (os.environ.get(ENV_LOGIN_URL) or DEFAULT_LOGIN_URL).rstrip("/")
    name = urllib.parse.quote(_key_name())

    if no_browser:
        url = f"{login_url}/cli-auth?name={name}"
        # flush: the URL must appear even when stdout is piped (block-buffered)
        print(
            "Open this URL in a browser, approve the request, then paste "
            f"the code shown:\n\n  {url}\n",
            flush=True,
        )
        try:
            code = input("Code: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nlogin cancelled")
        if not code:
            sys.exit("no code entered")
    else:
        state = secrets.token_urlsafe(32)
        server = _CallbackServer(state)
        try:
            port = server.server_address[1]
            url = f"{login_url}/cli-auth?port={port}&state={state}&name={name}"
            # flush: the URL must appear even when stdout is piped (block-buffered)
            print(
                f"Your browser has been opened to authorize the CLI:\n\n  {url}\n",
                flush=True,
            )
            if not webbrowser.open(url):
                print(
                    "Could not open a browser automatically; open the URL above "
                    "manually, or run `queria login --no-browser`.",
                    file=sys.stderr,
                )
            print("Waiting for approval in the browser...", flush=True)
            code = _wait_for_code(server, _TIMEOUT_S)
        finally:
            server.server_close()
        if code is None:
            sys.exit(
                "login timed out after 5 minutes; run `queria login` again "
                "or try `queria login --no-browser`"
            )

    try:
        token = _exchange(login_url, code)
        # Reject anything that could break out of the CREATE SECRET literal,
        # even from a trusted server (defense in depth).
        auth.validate_token(token)
        path = auth.set_token(token)
    except (RuntimeError, ValueError) as exc:
        sys.exit(str(exc))
    print(f"Logged in. Token saved to {path}")
    print("The token expires in 90 days; run `queria login` again to renew it.")
