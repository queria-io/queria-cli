"""API token resolution and config file management.

Tokens raise the rate limit on data.queria.io. A token is resolved in
priority order: the ``--token`` CLI flag, the ``QUERIA_TOKEN`` environment
variable, then the ``token`` key in ``~/.config/queria/config.toml``
(``$XDG_CONFIG_HOME`` is honored).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

ENV_VAR = "QUERIA_TOKEN"

# Tokens are embedded into a CREATE SECRET statement (DDL cannot be
# parameterized), so restrict them to characters that cannot break out of
# the SQL string literal.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_token(token: str) -> None:
    """Reject tokens containing anything but alphanumerics, ``_`` and ``-``."""
    if not _TOKEN_RE.match(token):
        raise ValueError(
            "invalid token: only alphanumerics, '_' and '-' are allowed"
        )


def config_path() -> Path:
    """Path of the queria config file, honoring ``$XDG_CONFIG_HOME``."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "queria" / "config.toml"


def read_config() -> dict:
    """Read the config file; missing or unreadable files yield ``{}``."""
    try:
        with open(config_path(), "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _write_config(config: dict) -> Path:
    """Write scalar config values as TOML with owner-only permissions."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in config.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            # TOML basic strings share JSON's escape rules.
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("".join(f"{line}\n" for line in lines))
    path.chmod(0o600)
    return path


def set_token(token: str) -> Path:
    """Validate ``token`` and persist it to the config file."""
    validate_token(token)
    config = read_config()
    config["token"] = token
    return _write_config(config)


def clear_token() -> bool:
    """Remove the token from the config file. Returns True if one was set."""
    config = read_config()
    if "token" not in config:
        return False
    del config["token"]
    _write_config(config)
    return True


def resolve_token(flag: str | None = None) -> tuple[str, str] | tuple[None, None]:
    """Resolve the API token as ``(token, source)``.

    ``source`` is ``"flag"``, ``"env"`` or ``"config"``; ``(None, None)``
    means no token is configured.
    """
    if flag:
        return flag, "flag"
    env = os.environ.get(ENV_VAR)
    if env:
        return env, "env"
    token = read_config().get("token")
    if isinstance(token, str) and token:
        return token, "config"
    return None, None
