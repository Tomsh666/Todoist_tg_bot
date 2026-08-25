from __future__ import annotations

import logging
import time
from collections import defaultdict

from aiogram import Bot

logger = logging.getLogger(__name__)


class AdminAlertManager:
    def __init__(self, bot: Bot, admin_user_id: int, window_seconds: float = 300.0, clock=time.monotonic) -> None:
        self.bot = bot
        self.admin_user_id = admin_user_id
        self.window_seconds = window_seconds
        self._clock = clock
        self._last_sent: defaultdict[str, float] = defaultdict(lambda: float("-inf"))

    async def notify(self, category: str, update_id: int) -> None:
        now = self._clock()
        if now - self._last_sent[category] < self.window_seconds:
            return
        self._last_sent[category] = now
        try:
            await self.bot.send_message(
                self.admin_user_id,
                f"Системная ошибка: {category} (update_id={update_id})",
            )
        except Exception:
            logger.exception("could_not_notify_admin category=%s", category)

