import time
from typing import Dict

CONTEXT_EXPIRY_SECONDS = 900
USER_CONTEXT: Dict[int, dict] = {}
LAST_MESSAGE_FINGERPRINT: Dict[int, tuple] = {}
LAST_UPDATE_ID: Dict[int, int] = {}


def get_user_context(user_id: int) -> dict:
    ctx = USER_CONTEXT.get(user_id, {})
    return ctx if ctx else {}


def set_user_context(user_id: int, **kwargs) -> None:
    ctx = USER_CONTEXT.get(user_id, {})
    ctx.update(kwargs)
    ctx['updated_at'] = time.time()
    USER_CONTEXT[user_id] = ctx


def clear_user_context(user_id: int) -> None:
    USER_CONTEXT.pop(user_id, None)


def is_duplicate_message(user_id: int, text: str, message_id: int | None = None, window_seconds: int = 1) -> bool:
    if message_id is not None:
        last_message_id = LAST_UPDATE_ID.get(user_id)
        if last_message_id == message_id:
            return True
        LAST_UPDATE_ID[user_id] = message_id

    now = time.time()
    last = LAST_MESSAGE_FINGERPRINT.get(user_id)
    fingerprint = text.strip()
    if last:
        last_text, last_time = last
        if last_text == fingerprint and (now - last_time) <= window_seconds:
            return True
    LAST_MESSAGE_FINGERPRINT[user_id] = (fingerprint, now)
    return False


def is_context_expired(ctx: dict) -> bool:
    updated_at = ctx.get('updated_at', 0)
    return (time.time() - updated_at) > CONTEXT_EXPIRY_SECONDS
