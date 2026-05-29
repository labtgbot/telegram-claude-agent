from dataclasses import dataclass
from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

DELETE_MESSAGES_CHUNK_SIZE = 100


class DeleteMessagesError(Exception):
    """Raised when ``deleteMessages`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


@dataclass(frozen=True)
class DeleteMessagesChunkError:
    message_ids: list[int]
    message: str
    error_code: Optional[int] = None


@dataclass(frozen=True)
class DeleteMessagesResult:
    chat_id: int
    requested_count: int
    deleted_count: int
    failed_chunks: list[DeleteMessagesChunkError]

    @property
    def ok(self) -> bool:
        return not self.failed_chunks


def _chunk_message_ids(message_ids: list[int]) -> list[list[int]]:
    return [
        message_ids[index : index + DELETE_MESSAGES_CHUNK_SIZE]
        for index in range(0, len(message_ids), DELETE_MESSAGES_CHUNK_SIZE)
    ]


async def _delete_messages_chunk(
    bot: Any,
    *,
    chat_id: int,
    message_ids: list[int],
) -> bool:
    return await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)


async def perform_delete_messages(
    bot: Any,
    *,
    chat_id: int,
    message_ids: list[int],
) -> DeleteMessagesResult:
    """Delete messages through typed aiogram API with 100-id chunking.

    Telegram ``deleteMessages`` accepts 1-100 message ids per request and skips
    messages that cannot be found. The pinned ``aiogram==3.3.0`` exposes the
    typed ``Bot.delete_messages()`` wrapper, so this helper adds validation,
    chunking and partial-error reporting around that API. Telegram still
    enforces message age, dice-message timing, bot ownership and
    ``can_delete_messages`` moderation rights.
    """
    if not message_ids:
        raise DeleteMessagesError("at least one message_id is required.")
    if any(message_id <= 0 for message_id in message_ids):
        raise DeleteMessagesError("message_ids must be positive integers.")

    deleted_count = 0
    failed_chunks: list[DeleteMessagesChunkError] = []
    chunks = _chunk_message_ids(message_ids)

    for chunk in chunks:
        try:
            await _delete_messages_chunk(
                bot,
                chat_id=chat_id,
                message_ids=chunk,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "delete_messages_chunk_failed",
                chat_id=chat_id,
                message_count=len(chunk),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            failed_chunks.append(
                DeleteMessagesChunkError(
                    message_ids=chunk,
                    message=str(exc),
                )
            )
            continue

        deleted_count += len(chunk)
        logger.info(
            "messages_deleted_chunk",
            chat_id=chat_id,
            message_count=len(chunk),
        )

    logger.info(
        "delete_messages_completed",
        chat_id=chat_id,
        requested_count=len(message_ids),
        deleted_count=deleted_count,
        failed_chunk_count=len(failed_chunks),
    )
    return DeleteMessagesResult(
        chat_id=chat_id,
        requested_count=len(message_ids),
        deleted_count=deleted_count,
        failed_chunks=failed_chunks,
    )


def format_delete_messages_result(result: DeleteMessagesResult) -> str:
    """Format ``deleteMessages`` result for HTML responses."""
    lines = [
        "<b>deleteMessages</b>",
        f"Chat ID: {escape(str(result.chat_id))}",
        f"Requested: {result.requested_count}",
        f"Deleted chunks count as: {result.deleted_count}",
        f"Failed chunks: {len(result.failed_chunks)}",
    ]
    if result.failed_chunks:
        lines.append("Partial errors:")
        for index, failure in enumerate(result.failed_chunks, start=1):
            error_code = f" [{failure.error_code}]" if failure.error_code else ""
            lines.append(
                f"{index}. ids {escape(str(failure.message_ids))}:"
                f"{error_code} {escape(failure.message)}"
            )
    return "\n".join(lines)
