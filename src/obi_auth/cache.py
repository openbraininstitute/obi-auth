"""Token cache module."""

from datetime import UTC, datetime

import jwt
from cryptography.fernet import Fernet, InvalidToken

from obi_auth.config import settings
from obi_auth.storage import Storage
from obi_auth.typedef import TokenInfo


class TokenCache:
    """Token cache."""

    token_info: TokenInfo | None = None

    def __init__(self, storage: Storage):
        """Initialize the token cache."""
        self._storage = storage
        self._cipher = Fernet(key=settings.secret_key)

    def get(self) -> str | None:
        """Get a cached token if valid, else None."""
        if self._storage.empty():
            return None
        try:
            token_info = self._storage.read()
            return self._cipher.decrypt_at_time(
                token=token_info.token,
                ttl=token_info.ttl,
                current_time=_now(),
            ).decode()
        except InvalidToken:
            self._storage.clear()
            return None

    def set(self, token: str) -> None:
        """Store a new token in the cache."""
        creation_time, time_to_live = _get_token_times(token)
        fernet_token: bytes = self._cipher.encrypt_at_time(
            data=token.encode(encoding="utf-8"),
            current_time=creation_time,
        )
        token_info = TokenInfo(
            token=fernet_token,
            ttl=time_to_live,
        )
        self._storage.write(token_info)


def _now() -> int:
    """Return UTC timestamp now."""
    return int(datetime.now(UTC).timestamp())


def _get_token_times(token: str) -> tuple[int, int]:
    """Get the creation time and time to live of a token."""
    info = jwt.decode(token.encode(), options={"verify_signature": False})
    return info["iat"], info["exp"] - info["iat"]
