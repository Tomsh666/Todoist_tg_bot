from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .alerts import AdminAlertManager
from .config import Settings
from .dedup import UpdateDeduplicator
from .limits import SlidingWindowRateLimiter
from .todoist import TodoistClient, TodoistSystemError, TodoistUserError
from .validation import UserInputError, validate_message

logger = logging.getLogger(__name__)

DONE = "Готово"
USER_ERROR = "Ошибка"
SYSTEM_ERROR = "Системная ошибка"


def _request_id(message: Message) -> str:
    digest = hashlib.sha256(f"{message.chat.id}:{message.message_id}".encode()).hexdigest()
    return f"tg-{digest[:32]}"


def create_router(
    settings: Settings,
    todoist: TodoistClient,
    alerts: AdminAlertManager,
    deduplicator: UpdateDeduplicator | None = None,
    limiter: SlidingWindowRateLimiter | None = None,
) -> Router:
    router = Router(name="todoist_capture")
    deduplicator = deduplicator or UpdateDeduplicator()
    limiter = limiter or SlidingWindowRateLimiter(settings.rate_limit_count, settings.rate_limit_window_seconds)

    async def send_user_error(message: Message) -> None:
        await message.answer(USER_ERROR)

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        sender = message.from_user
        if sender is None or sender.id not in settings.allowed_user_ids or message.chat.type != "private":
            return
        await message.answer(
            "Отправьте короткий текст — я создам задачу в Todoist.\n"
            "До 50 символов, можно написать дату: «позвонить завтра в 15:00»."
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        sender = message.from_user
        if sender is None or sender.id not in settings.allowed_user_ids or message.chat.type != "private":
            return
        await message.answer(
            "Пример: купить молоко завтра\n"
            "Задача попадёт во Входящие и будет отмечена вашим @username."
        )

    @router.message()
    async def capture(message: Message) -> None:
        sender = message.from_user
        if sender is None or sender.id not in settings.allowed_user_ids:
            return
        if message.chat.type != "private":
            return

        update_id = message.message_id
        message_key = (message.chat.id, message.message_id)
        if not deduplicator.first_seen(message_key):
            return
        if not limiter.allow(sender.id):
            await send_user_error(message)
            return

        started = time.monotonic()
        try:
            validated = validate_message(
                message,
                allowed_user_ids=settings.allowed_user_ids,
                max_length=settings.max_text_length,
            )
            await todoist.create_task(validated.text, validated.username, _request_id(message))
        except (UserInputError, TodoistUserError):
            await send_user_error(message)
            logger.info("user_error user_id=%s username=%s", sender.id, sender.username)
            return
        except TodoistSystemError as exc:
            category = str(exc)
            logger.error(
                "system_error category=%s user_id=%s username=%s latency_ms=%d",
                category,
                sender.id,
                sender.username,
                int((time.monotonic() - started) * 1000),
            )
            await message.answer(SYSTEM_ERROR)
            await alerts.notify(category, update_id)
            return
        except Exception:
            logger.exception("unexpected_error user_id=%s username=%s", sender.id, sender.username)
            await message.answer(SYSTEM_ERROR)
            await alerts.notify("unexpected_error", update_id)
            return

        logger.info(
            "task_created user_id=%s username=%s latency_ms=%d",
            sender.id,
            sender.username,
            int((time.monotonic() - started) * 1000),
        )
        await message.answer(DONE)

    return router


async def run(settings: Settings, heartbeat_task_factory: Callable[[str], Awaitable[None]]) -> None:
    bot = Bot(token=settings.telegram_bot_token)
    todoist = TodoistClient(
        api_token=settings.todoist_api_token,
        base_url=settings.todoist_api_url,
        attempts=settings.retry_attempts,
        budget_seconds=settings.retry_budget_seconds,
    )
    await bot.get_me()
    await todoist.check_connection()

    alerts = AdminAlertManager(bot, settings.admin_user_id, settings.alert_window_seconds)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_router(settings, todoist, alerts))
    heartbeat_task = asyncio.create_task(heartbeat_task_factory(settings.heartbeat_path))
    try:
        await dispatcher.start_polling(bot, allowed_updates=["message"])
    finally:
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
        await bot.session.close()

