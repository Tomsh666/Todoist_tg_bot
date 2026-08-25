from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when required runtime configuration is invalid."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"missing required setting: {name}")
    return value


def _user_ids(value: str) -> frozenset[int]:
    result: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            user_id = int(item)
        except ValueError as exc:
            raise ConfigError("ALLOWED_USER_IDS must contain comma-separated integers") from exc
        if user_id <= 0:
            raise ConfigError("Telegram user IDs must be positive")
        result.add(user_id)
    if not result:
        raise ConfigError("ALLOWED_USER_IDS must contain at least one ID")
    return frozenset(result)


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    todoist_api_token: str
    allowed_user_ids: frozenset[int]
    admin_user_id: int
    max_text_length: int = 50
    rate_limit_count: int = 10
    rate_limit_window_seconds: float = 60.0
    retry_attempts: int = 3
    retry_budget_seconds: float = 10.0
    alert_window_seconds: float = 300.0
    heartbeat_path: str = "/tmp/todoist-tg-bot.heartbeat"
    todoist_api_url: str = "https://api.todoist.com/api/v1"

    @classmethod
    def from_env(cls) -> "Settings":
        allowed = _user_ids(_required("ALLOWED_USER_IDS"))
        try:
            admin_id = int(_required("ADMIN_USER_ID"))
        except ValueError as exc:
            raise ConfigError("ADMIN_USER_ID must be an integer") from exc
        if admin_id <= 0 or admin_id not in allowed:
            raise ConfigError("ADMIN_USER_ID must be a positive ID present in ALLOWED_USER_IDS")
        return cls(
            telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
            todoist_api_token=_required("TODOIST_API_TOKEN"),
            allowed_user_ids=allowed,
            admin_user_id=admin_id,
            heartbeat_path=os.getenv("HEARTBEAT_PATH", "/tmp/todoist-tg-bot.heartbeat"),
            todoist_api_url=os.getenv("TODOIST_API_URL", "https://api.todoist.com/api/v1").rstrip("/"),
        )

