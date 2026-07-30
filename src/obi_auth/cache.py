"""Token cache module."""

import time

import jwt
from cryptography.fernet import Fernet, InvalidToken

from obi_auth.config import settings
from obi_auth.storage import Storage
from obi_auth.typedef import CachedTokenInfo, KeycloakTokenInfo, TokenInfo
from obi_auth.util import derive_fernet_key


class TokenCache:
    """Token cache."""

    def __init__(self):
        """Initialize the token cache."""
        self._cipher = Fernet(key=derive_fernet_key())

    def get(self, storage: Storage) -> TokenInfo | None:
        """Get a cached token if valid, else None."""
        if not (cached_token_info := storage.read()):
            return None
        try:
            decrypted_token = self._cipher.decrypt_at_time(
                token=cached_token_info.token,
                ttl=cached_token_info.ttl,
                current_time=_now(),
            ).decode()
            return KeycloakTokenInfo(access_token=decrypted_token)
        except InvalidToken:
            storage.clear()
            return None

    def set(self, token_info: TokenInfo, storage: Storage) -> None:
        """Store a new token in the cache."""
        token = token_info.access_token
        creation_time, time_to_live = _get_token_times(token)
        fernet_token: bytes = self._cipher.encrypt_at_time(
            data=token.encode(encoding="utf-8"),
            current_time=creation_time,
        )
        cached_token_info = CachedTokenInfo(
            token=fernet_token,
            ttl=time_to_live,
        )
        storage.write(cached_token_info)


def _now() -> int:
    """Return UTC timestamp now."""
    return int(time.time())


def _get_token_times(token: str) -> tuple[int, int]:
    """Get the creation time and time to live of a token."""
    info = jwt.decode(token.encode(), options={"verify_signature": False})
    effective_ttl = info["exp"] - info["iat"] - settings.EPSILON_TOKEN_TTL_SECONDS
    return info["iat"], effective_ttl
