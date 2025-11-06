import contextvars
from typing import Optional, Tuple

_request_id = contextvars.ContextVar("request_id", default="")
_user_id    = contextvars.ContextVar("user_id", default="")
_sid        = contextvars.ContextVar("sid", default="")

def set_request_id(rid: str | None) -> None:
    _request_id.set(rid)

def get_request_id() -> str:
    return _request_id.get()

def set_user_context(user_id: Optional[str] = None, sid: Optional[str] = None) -> None:
    if user_id is not None:
        _user_id.set(user_id or "")
    if sid is not None:
        _sid.set(sid or "")

def get_user_context() -> Tuple[str, str]:
    return _user_id.get(), _sid.get()