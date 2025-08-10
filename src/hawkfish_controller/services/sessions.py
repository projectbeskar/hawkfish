from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

DEFAULT_TTL_SECONDS = 8 * 60 * 60


@dataclass
class Session:
    token: str
    username: str
    created_at: float
    expires_at: float


class SessionStore:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._token_to_session: dict[str, Session] = {}

    def create_session(self, username: str) -> Session:
        token = secrets.token_urlsafe(24)
        now = time.time()
        session = Session(token=token, username=username, created_at=now, expires_at=now + self.ttl_seconds)
        self._token_to_session[token] = session
        return session

    def get(self, token: str) -> Session | None:
        session = self._token_to_session.get(token)
        if not session:
            return None
        if session.expires_at < time.time():
            self._token_to_session.pop(token, None)
            return None
        return session

    def delete(self, token: str) -> None:
        self._token_to_session.pop(token, None)


global_session_store = SessionStore()


