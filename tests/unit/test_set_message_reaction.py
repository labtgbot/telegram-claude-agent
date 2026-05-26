from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMessageReaction
from aiogram.types import ReactionTypeEmoji

from bot.handlers import commands
from bot.services.set_message_reaction import (
    REACTION_EMOJI,
    perform_set_message_reaction,
)

THUMBS_UP = "👍"
FIRE_EMOJI = "🔥"
HEART_EMOJI = "❤"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _message(text: str = "/react", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Service: perform_set_message_reaction
# ---------------------------------------------------------------------------


async def test_perform_set_message_reaction_minimal_call():
    bot = SimpleNamespace(set_message_reaction=AsyncMock(return_value=True))

    result = await perform_set_message_reaction(bot, chat_id=42, message_id=100)

    assert result is True
    bot.set_message_reaction.assert_awaited_once_with(
        chat_id=42,
        message_id=100,
        reaction=None,
        is_big=None,
    )


async def test_perform_set_message_reaction_with_emoji_reaction():
    reaction = [ReactionTypeEmoji(emoji=THUMBS_UP)]
    bot = SimpleNamespace(set_message_reaction=AsyncMock(return_value=True))

    result = await perform_set_message_reaction(
        bot,
        chat_id=10,
        message_id=200,
        reaction=reaction,
        is_big=False,
    )

    assert result is True
    bot.set_message_reaction.assert_awaited_once_with(
        chat_id=10,
        message_id=200,
        reaction=reaction,
        is_big=False,
    )


async def test_perform_set_message_reaction_with_big_animation():
    reaction = [ReactionTypeEmoji(emoji=FIRE_EMOJI)]
    bot = SimpleNamespace(set_message_reaction=AsyncMock(return_value=True))

    await perform_set_message_reaction(
        bot,
        chat_id=5,
        message_id=300,
        reaction=reaction,
        is_big=True,
    )

    _, kwargs = bot.set_message_reaction.await_args
    assert kwargs["is_big"] is True


async def test_perform_set_message_reaction_with_empty_reaction_removes_reactions():
    """Passing an empty list removes all bot reactions from the message."""
    bot = SimpleNamespace(set_message_reaction=AsyncMock(return_value=True))

    await perform_set_message_reaction(
        bot,
        chat_id=42,
        message_id=100,
        reaction=[],
    )

    _, kwargs = bot.set_message_reaction.await_args
    assert kwargs["reaction"] == []


async def test_perform_set_message_reaction_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetMessageReaction(chat_id=1, message_id=1),
        message="Bad Request: message not found",
    )
    bot = SimpleNamespace(set_message_reaction=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_message_reaction(bot, chat_id=1, message_id=1)


async def test_perform_set_message_reaction_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetMessageReaction(chat_id=2, message_id=1),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_message_reaction=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_message_reaction(bot, chat_id=2, message_id=1)


# ---------------------------------------------------------------------------
# REACTION_EMOJI constant
# ---------------------------------------------------------------------------


def test_reaction_emoji_contains_thumbs_up():
    assert THUMBS_UP in REACTION_EMOJI


def test_reaction_emoji_contains_fire():
    assert FIRE_EMOJI in REACTION_EMOJI


def test_reaction_emoji_does_not_contain_pizza():
    assert "🍕" not in REACTION_EMOJI


def test_reaction_emoji_is_non_empty():
    assert len(REACTION_EMOJI) > 0


# ---------------------------------------------------------------------------
# Handler: cmd_react — access control
# ---------------------------------------------------------------------------


async def test_cmd_react_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_message_reaction", AsyncMock())
    message = _message(text=f"/react 100 {THUMBS_UP}", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


# ---------------------------------------------------------------------------
# Handler: cmd_react — validation
# ---------------------------------------------------------------------------


async def test_cmd_react_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_message_reaction", AsyncMock())
    message = _message(text="/react", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "react usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_react_shows_usage_on_invalid_message_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_message_reaction", AsyncMock())
    message = _message(text="/react notanumber", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "react usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_react_rejects_unsupported_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_message_reaction", AsyncMock())
    message = _message(text="/react 100 🍕", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Unsupported reaction emoji" in args[0]


# ---------------------------------------------------------------------------
# Handler: cmd_react — successful calls
# ---------------------------------------------------------------------------


async def test_cmd_react_sets_emoji_reaction(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_message_reaction", AsyncMock(return_value=True)
    )
    message = _message(text=f"/react 100 {THUMBS_UP}", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_awaited_once()
    _, kwargs = commands.perform_set_message_reaction.await_args
    assert kwargs["chat_id"] == 42
    assert kwargs["message_id"] == 100
    assert kwargs["reaction"] is not None
    assert len(kwargs["reaction"]) == 1
    assert kwargs["reaction"][0].emoji == THUMBS_UP
    args, _ = message.answer.await_args
    assert THUMBS_UP in args[0]
    assert "100" in args[0]


async def test_cmd_react_removes_reactions_without_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_message_reaction", AsyncMock(return_value=True)
    )
    message = _message(text="/react 200", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_awaited_once()
    _, kwargs = commands.perform_set_message_reaction.await_args
    assert kwargs["reaction"] is None
    args, _ = message.answer.await_args
    assert "Removed reactions" in args[0]
    assert "200" in args[0]


async def test_cmd_react_passes_big_flag(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_message_reaction", AsyncMock(return_value=True)
    )
    message = _message(text=f"/react 100 {FIRE_EMOJI} big", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_awaited_once()
    _, kwargs = commands.perform_set_message_reaction.await_args
    assert kwargs["is_big"] is True


async def test_cmd_react_big_flag_without_emoji(monkeypatch):
    """``big`` without emoji should still pass through (no reaction, big=True)."""
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_message_reaction", AsyncMock(return_value=True)
    )
    message = _message(text="/react 100 big", chat_id=42)

    await commands.cmd_react(message)

    commands.perform_set_message_reaction.assert_awaited_once()
    _, kwargs = commands.perform_set_message_reaction.await_args
    # "big" without a preceding emoji means no emoji, is_big=True
    assert kwargs["reaction"] is None
    assert kwargs["is_big"] is True


# ---------------------------------------------------------------------------
# Handler: cmd_react — error handling
# ---------------------------------------------------------------------------


async def test_cmd_react_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetMessageReaction(chat_id=42, message_id=100),
        message="Bad Request: message not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_message_reaction", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/react 100 {THUMBS_UP}", chat_id=42)

    await commands.cmd_react(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the reaction" in args[0]


# ---------------------------------------------------------------------------
# Parser: _parse_react_args
# ---------------------------------------------------------------------------


def test_parse_react_args_no_args():
    assert commands._parse_react_args("/react") is None


def test_parse_react_args_invalid_message_id():
    assert commands._parse_react_args("/react notanumber") is None


def test_parse_react_args_message_id_only():
    result = commands._parse_react_args("/react 100")
    assert result == (100, None, False)


def test_parse_react_args_with_emoji():
    result = commands._parse_react_args(f"/react 100 {THUMBS_UP}")
    assert result == (100, THUMBS_UP, False)


def test_parse_react_args_with_emoji_and_big():
    result = commands._parse_react_args(f"/react 100 {FIRE_EMOJI} big")
    assert result == (100, FIRE_EMOJI, True)


def test_parse_react_args_big_without_emoji():
    result = commands._parse_react_args("/react 100 big")
    assert result == (100, None, True)


def test_parse_react_args_big_case_insensitive():
    result = commands._parse_react_args(f"/react 100 {HEART_EMOJI} BIG")
    assert result == (100, HEART_EMOJI, True)


def test_parse_react_args_negative_message_id():
    # Negative ids should be passed through; Telegram will reject them.
    result = commands._parse_react_args("/react -5")
    assert result == (-5, None, False)


def test_parse_react_args_zero_message_id():
    result = commands._parse_react_args("/react 0")
    assert result == (0, None, False)
