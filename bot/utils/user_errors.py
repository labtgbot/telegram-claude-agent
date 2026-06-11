from typing import Any


GENERIC_USER_ERROR_SUFFIX = "Please try again later."


def format_user_error(summary: str) -> str:
    """Return a user-facing error without internal exception details."""
    summary = summary.strip().rstrip(".")
    return f"{summary}. {GENERIC_USER_ERROR_SUFFIX}"


def log_user_error_context(logger: Any, event: str, exc: Exception, **context: Any) -> None:
    """Log the full exception while keeping the user-facing response generic."""
    logger.exception(
        event,
        error_type=type(exc).__name__,
        error=str(exc),
        **context,
    )
