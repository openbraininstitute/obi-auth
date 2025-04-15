"""Token cache module."""

import time

import jwt
from cryptography.fernet import Fernet, InvalidToken

from obi_auth.storage import Storage
from obi_auth.typedef import TokenInfo
from obi_auth.util import derive_fernet_key


class TokenCache:
    """Token cache."""

    token_info: TokenInfo | None = None

    def __init__(self):
        """Initialize the token cache."""
        self._cipher = Fernet(key=derive_fernet_key())

    def get(self, storage: Storage) -> str | None:
        """Get a cached token if valid, else None."""
        if not (token_info := storage.read()):
            return None
        try:
            return self._cipher.decrypt_at_time(
                token=token_info.token,
                ttl=token_info.ttl,
                current_time=_now(),
            ).decode()
        except InvalidToken:
            storage.clear()
            return None

    def set(self, token: str, storage: Storage) -> None:
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
        storage.write(token_info)


def _now() -> int:
    """Return UTC timestamp now."""
    return int(time.time())


def _get_token_times(token: str) -> tuple[int, int]:
    """Get the creation time and time to live of a token."""
    info = jwt.decode(token.encode(), options={"verify_signature": False})
    return info["iat"], info["exp"] - info["iat"]
