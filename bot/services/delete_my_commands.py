from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChatMember,
    BotCommandScopeDefault,
)

logger = structlog.get_logger()

BotCommandScope = (
    BotCommandScopeDefault
    | BotCommandScopeAllPrivateChats
    | BotCommandScopeAllGroupChats
    | BotCommandScopeAllChatAdministrators
    | BotCommandScopeChat
    | BotCommandScopeChatAdministrators
    | BotCommandScopeChatMember
)


async def perform_delete_my_commands(
    bot: Any,
    *,
    scope: BotCommandScope | None = None,
    language_code: str | None = None,
) -> bool:
    """Delete bot commands for a scope/language via the typed aiogram API.

    Calls Telegram ``deleteMyCommands`` through ``Bot.delete_my_commands()``.
    The method does not require chat administrator rights, but this project
    exposes it as a deny-by-default admin command because it changes the bot's
    public command menu and is commonly used before command synchronization.
    """
    try:
        result = await bot.delete_my_commands(
            scope=scope,
            language_code=language_code,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "delete_my_commands_failed",
            scope=_scope_label(scope),
            language_code=language_code,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "delete_my_commands_succeeded",
        scope=_scope_label(scope),
        language_code=language_code,
    )
    return result


def format_delete_my_commands_result(
    *,
    scope: BotCommandScope | None = None,
    language_code: str | None = None,
) -> str:
    """Format a successful ``deleteMyCommands`` result for HTML responses."""
    return "\n".join(
        [
            "<b>deleteMyCommands</b>",
            "Status: deleted bot commands.",
            f"Scope: {escape(_scope_label(scope))}",
            f"Language: {escape(language_code or 'default')}",
        ]
    )


def _scope_label(scope: BotCommandScope | None) -> str:
    if scope is None:
        return "default"
    if isinstance(scope, BotCommandScopeChat):
        return f"chat {scope.chat_id}"
    if isinstance(scope, BotCommandScopeChatAdministrators):
        return f"chat_administrators {scope.chat_id}"
    if isinstance(scope, BotCommandScopeChatMember):
        return f"chat_member {scope.chat_id}:{scope.user_id}"
    return str(scope.type.value)
