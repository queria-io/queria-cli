from __future__ import annotations

import pytest

from queria import auth
from queria.auth import tomllib  # tomli fallback on Python 3.10


def test_config_path_honors_xdg_config_home(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert auth.config_path() == tmp_path / "queria" / "config.toml"


def test_set_token_writes_toml_with_owner_only_permissions() -> None:
    path = auth.set_token("tok_abc-123")
    assert path == auth.config_path()
    assert (path.stat().st_mode & 0o777) == 0o600
    with open(path, "rb") as f:
        assert tomllib.load(f) == {"token": "tok_abc-123"}


def test_set_token_preserves_other_keys() -> None:
    auth.config_path().parent.mkdir(parents=True)
    auth.config_path().write_text('other = "keep"\n')
    path = auth.set_token("tok123")
    with open(path, "rb") as f:
        assert tomllib.load(f) == {"other": "keep", "token": "tok123"}


def test_set_token_rejects_invalid_characters() -> None:
    with pytest.raises(ValueError, match="invalid token"):
        auth.set_token("tok'; DROP SECRET x; --")
    assert not auth.config_path().exists()


def test_clear_token() -> None:
    auth.set_token("tok123")
    assert auth.clear_token() is True
    assert auth.read_config() == {}
    assert auth.clear_token() is False


def test_resolve_token_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    assert auth.resolve_token() == (None, None)
    auth.set_token("configtok")
    assert auth.resolve_token() == ("configtok", "config")
    monkeypatch.setenv("QUERIA_TOKEN", "envtok")
    assert auth.resolve_token() == ("envtok", "env")
    assert auth.resolve_token("flagtok") == ("flagtok", "flag")


def test_read_config_ignores_broken_file() -> None:
    auth.config_path().parent.mkdir(parents=True)
    auth.config_path().write_text("not toml [")
    assert auth.read_config() == {}
