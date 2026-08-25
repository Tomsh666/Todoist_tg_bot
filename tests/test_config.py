from __future__ import annotations

import pytest

from app.config import ConfigError, Settings


def set_valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TODOIST_API_TOKEN", "todoist-token")
    monkeypatch.setenv("ALLOWED_USER_IDS", "123,456")
    monkeypatch.setenv("ADMIN_USER_ID", "123")


def test_settings_parse_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_env(monkeypatch)
    settings = Settings.from_env()
    assert settings.allowed_user_ids == frozenset({123, 456})
    assert settings.admin_user_id == 123
    assert settings.max_text_length == 50


def test_admin_must_be_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_env(monkeypatch)
    monkeypatch.setenv("ADMIN_USER_ID", "999")
    with pytest.raises(ConfigError, match="present in ALLOWED_USER_IDS"):
        Settings.from_env()

