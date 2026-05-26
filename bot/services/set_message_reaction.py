from typing import Any, List, Optional, Union

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ReactionTypeCustomEmoji, ReactionTypeEmoji

logger = structlog.get_logger()

# Emoji reactions supported by Telegram Bot API as of Bot API 7.0 (aiogram 3.3.0).
# This list matches the ``ReactionTypeEmoji.emoji`` field documentation exactly.
REACTION_EMOJI = frozenset(
    {
        "👍",
        "👎",
        "❤",
        "🔥",
        "🥰",
        "👏",
        "😁",
        "🤔",
        "🤯",
        "😱",
        "🤬",
        "😢",
        "🎉",
        "🤩",
        "🤮",
        "💩",
        "🙏",
        "👌",
        "🕊",
        "🤡",
        "🥱",
        "🥴",
        "😍",
        "🐳",
        "❤‍🔥",
        "🌚",
        "🌭",
        "💯",
        "🤣",
        "⚡",
        "🍌",
        "🏆",
        "💔",
        "🤨",
        "😐",
        "🍓",
        "🍾",
        "💋",
        "🖕",
        "😈",
        "😴",
        "😭",
        "🤓",
        "👻",
        "👨‍💻",
        "👀",
        "🎃",
        "🙈",
        "😇",
        "😨",
        "🤝",
        "✍",
        "🤗",
        "🫡",
        "🎅",
        "🎄",
        "☃",
        "💅",
        "🤪",
        "🗿",
        "🆒",
        "💘",
        "🙉",
        "🦄",
        "😘",
        "💊",
        "🙊",
        "😎",
        "👾",
        "🤷‍♂",
        "🤷",
        "🤷‍♀",
        "😡",
    }
)


class SetMessageReactionError(Exception):
    """Raised when the reaction cannot be set due to a validation error."""


async def perform_set_message_reaction(
    bot: Any,
    *,
    chat_id: int,
    message_id: int,
    reaction: Optional[List[Union[ReactionTypeEmoji, ReactionTypeCustomEmoji]]] = None,
    is_big: Optional[bool] = None,
) -> bool:
    """Set a reaction on a message via the typed aiogram API.

    Calls the typed aiogram ``Bot.set_message_reaction()`` wrapper for the
    Telegram ``setMessageReaction`` method (Bot API 7.0, supported since
    ``aiogram==3.3.0``).

    The bot does not require any special administrative permissions to set
    reactions, but:

    * Service messages cannot be reacted to.
    * Automatically forwarded messages from a channel to its discussion group
      have the same available reactions as messages in the channel.
    * In albums, bots must react to the first message of the album.
    * As a non-premium user, a bot can set at most **one** reaction per
      message. Premium bots can set up to three.
    * Custom emoji reactions can only be used if the emoji is already present
      on the message or explicitly allowed by chat administrators.
    * Passing an empty list (or ``None``) for ``reaction`` removes all
      reactions the bot has placed on the message.

    Parameters
    ----------
    chat_id:
        Unique identifier for the target chat.
    message_id:
        Identifier of the target message.
    reaction:
        New list of reaction types to set on the message. Pass an empty list
        or ``None`` to remove all reactions placed by the bot. Each element
        must be either a :class:`~aiogram.types.ReactionTypeEmoji` or a
        :class:`~aiogram.types.ReactionTypeCustomEmoji` instance.
    is_big:
        When ``True`` Telegram plays the reaction with a big animation.
        Defaults to ``False`` (Telegram side).

    Returns
    -------
    bool
        ``True`` on success.

    Raises
    ------
    TelegramAPIError
        Re-raised without modification after logging, so callers can handle it.
    """
    try:
        result = await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=reaction,
            is_big=is_big,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_message_reaction_failed",
            chat_id=chat_id,
            message_id=message_id,
            reaction_count=len(reaction) if reaction else 0,
            is_big=is_big,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "message_reaction_set",
        chat_id=chat_id,
        message_id=message_id,
        reaction_count=len(reaction) if reaction else 0,
        is_big=bool(is_big),
    )
    return result
