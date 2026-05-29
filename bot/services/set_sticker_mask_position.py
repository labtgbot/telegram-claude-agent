from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MASK_POSITION_POINTS = {"forehead", "eyes", "mouth", "chin"}


class SetStickerMaskPositionError(Exception):
    """Raised when raw ``setStickerMaskPosition`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_mask_position(
    point: str,
    x_shift: float,
    y_shift: float,
    scale: float,
) -> dict[str, float | str]:
    """Validate and normalize a Telegram ``MaskPosition`` payload."""
    normalized_point = point.strip().lower()
    if normalized_point not in MASK_POSITION_POINTS:
        raise SetStickerMaskPositionError(
            "point must be one of: chin, eyes, forehead, mouth."
        )
    if scale <= 0:
        raise SetStickerMaskPositionError("scale must be greater than zero.")
    return {
        "point": normalized_point,
        "x_shift": x_shift,
        "y_shift": y_shift,
        "scale": scale,
    }


async def perform_set_sticker_mask_position(
    bot: Any,
    *,
    sticker: str,
    mask_position: dict[str, float | str] | None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Change or clear the mask position for a bot-created mask sticker."""
    try:
        normalized_sticker = _validate_required_text(sticker, "sticker")
    except Exception as exc:
        raise SetStickerMaskPositionError(str(exc)) from exc

    payload: dict[str, Any] = {"sticker": normalized_sticker}
    if mask_position is not None:
        try:
            payload["mask_position"] = validate_mask_position(
                str(mask_position["point"]),
                float(mask_position["x_shift"]),
                float(mask_position["y_shift"]),
                float(mask_position["scale"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SetStickerMaskPositionError(
                "mask_position must contain point, x_shift, y_shift and scale."
            ) from exc

    url = _build_api_url(bot, "setStickerMaskPosition")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_mask_position_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            has_mask_position=mask_position is not None,
        )
        raise SetStickerMaskPositionError(
            f"setStickerMaskPosition request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_mask_position_failed",
            error_code=error_code,
            error=description,
            has_mask_position=mask_position is not None,
        )
        raise SetStickerMaskPositionError(description, error_code=error_code)

    logger.info(
        "sticker_mask_position_set",
        has_mask_position=mask_position is not None,
    )
    return bool(data.get("result"))


def format_set_sticker_mask_position_result(
    *,
    sticker: str,
    mask_position: dict[str, float | str] | None,
) -> str:
    """Format a successful ``setStickerMaskPosition`` result for HTML."""
    lines = [
        "<b>setStickerMaskPosition</b>",
        "Sticker mask position updated.",
        f"Sticker file id: <code>{escape(sticker)}</code>",
    ]
    if mask_position is None:
        lines.append("Mask position: cleared.")
    else:
        lines.extend(
            [
                f"Point: <code>{escape(str(mask_position['point']))}</code>",
                f"X shift: <code>{mask_position['x_shift']}</code>",
                f"Y shift: <code>{mask_position['y_shift']}</code>",
                f"Scale: <code>{mask_position['scale']}</code>",
            ]
        )
    return "\n".join(lines)
