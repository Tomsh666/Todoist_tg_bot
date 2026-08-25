from __future__ import annotations

from dataclasses import dataclass


class UserInputError(ValueError):
    """A message cannot be converted into a task under bot rules."""


@dataclass(frozen=True, slots=True)
class ValidatedMessage:
    text: str
    username: str


def validate_message(message: object, *, allowed_user_ids: frozenset[int], max_length: int) -> ValidatedMessage:
    chat = getattr(message, "chat", None)
    if getattr(chat, "type", None) != "private":
        raise UserInputError("private chat required")

    sender = getattr(message, "from_user", None)
    user_id = getattr(sender, "id", None)
    if user_id not in allowed_user_ids:
        raise PermissionError("sender is not allowlisted")

    if (
        getattr(message, "forward_origin", None) is not None
        or getattr(message, "forward_from", None) is not None
        or getattr(message, "forward_from_chat", None) is not None
        or getattr(message, "forward_sender_name", None) is not None
        or getattr(message, "reply_to_message", None) is not None
    ):
        raise UserInputError("forwarded and replied messages are not accepted")

    username = getattr(sender, "username", None)
    if not username:
        raise UserInputError("Telegram username is required")

    raw_text = getattr(message, "text", None)
    if not isinstance(raw_text, str):
        raise UserInputError("text messages only")
    text = raw_text.strip()
    if not text:
        raise UserInputError("empty text")
    if len(text) > max_length:
        raise UserInputError("text is too long")
    return ValidatedMessage(text=text, username=username)

