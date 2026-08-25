from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.validation import UserInputError, validate_message


def message(text: str | None = "купить молоко", **kwargs: object) -> SimpleNamespace:
    sender = SimpleNamespace(id=123, username="tomsh")
    chat = SimpleNamespace(type="private")
    return SimpleNamespace(from_user=sender, chat=chat, text=text, **kwargs)


def test_validation_trims_edges_and_preserves_internal_newline() -> None:
    result = validate_message(
        message("  купить\nмолоко  "), allowed_user_ids=frozenset({123}), max_length=50
    )
    assert result.text == "купить\nмолоко"
    assert result.username == "tomsh"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"text": ""},
        {"text": "x" * 51},
        {"forward_origin": object()},
        {"reply_to_message": object()},
    ],
)
def test_invalid_messages_raise_user_error(kwargs: dict[str, object]) -> None:
    with pytest.raises(UserInputError):
        validate_message(message(**kwargs), allowed_user_ids=frozenset({123}), max_length=50)


def test_missing_username_is_rejected() -> None:
    msg = message()
    msg.from_user.username = None
    with pytest.raises(UserInputError, match="username"):
        validate_message(msg, allowed_user_ids=frozenset({123}), max_length=50)


def test_non_allowlisted_user_raises_permission_error() -> None:
    with pytest.raises(PermissionError):
        validate_message(message(), allowed_user_ids=frozenset({999}), max_length=50)

