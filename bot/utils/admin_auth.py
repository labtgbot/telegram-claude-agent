from collections.abc import Sequence


def _is_private_admin_request(chat_id: int, user_id: int | None) -> bool:
    if user_id is None:
        return chat_id > 0
    return chat_id == user_id


def is_admin_sender_allowed(
    *,
    chat_id: int,
    user_id: int | None,
    admin_user_ids: Sequence[int],
) -> bool:
    if admin_user_ids:
        return user_id in admin_user_ids if user_id is not None else False

    return _is_private_admin_request(chat_id, user_id)


def is_admin_action_allowed(
    *,
    chat_id: int,
    user_id: int | None,
    admin_chat_ids: Sequence[int],
    admin_user_ids: Sequence[int],
) -> bool:
    return bool(
        admin_chat_ids
        and chat_id in admin_chat_ids
        and is_admin_sender_allowed(
            chat_id=chat_id,
            user_id=user_id,
            admin_user_ids=admin_user_ids,
        )
    )


def is_admin_or_allowed_chat(
    *,
    chat_id: int,
    user_id: int | None,
    admin_chat_ids: Sequence[int],
    allowed_chat_ids: Sequence[int],
    admin_user_ids: Sequence[int],
) -> bool:
    trusted_chat_ids = admin_chat_ids or allowed_chat_ids
    return bool(
        trusted_chat_ids
        and chat_id in trusted_chat_ids
        and is_admin_sender_allowed(
            chat_id=chat_id,
            user_id=user_id,
            admin_user_ids=admin_user_ids,
        )
    )
