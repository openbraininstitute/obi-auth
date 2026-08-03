"""Token cache module."""

import time

import jwt
from cryptography.fernet import Fernet, InvalidToken

from obi_auth.config import settings
from obi_auth.storage import Storage
from obi_auth.typedef import (
    AuthManagerTokenInfo,
    CachedAuthManagerTokenInfo,
    CachedTokenInfo,
    KeycloakTokenInfo,
)
from obi_auth.util import derive_fernet_key


class BaseTokenCache:
    """Shared Fernet helpers for token caches."""

    def __init__(self):
        """Initialize the token cache."""
        self._cipher = Fernet(key=derive_fernet_key())

    def _encrypt_access_token(self, access_token: str) -> tuple[bytes, int]:
        creation_time, time_to_live = _get_token_times(access_token)
        fernet_token = self._cipher.encrypt_at_time(
            data=access_token.encode(encoding="utf-8"),
            current_time=creation_time,
        )
        return fernet_token, time_to_live

    def _decrypt_access_token(self, token: bytes, ttl: int) -> str:
        return self._cipher.decrypt_at_time(
            token=token,
            ttl=ttl,
            current_time=_now(),
        ).decode()


class TokenCache(BaseTokenCache):
    """Cache for Keycloak access tokens."""

    def get(self, storage: Storage) -> KeycloakTokenInfo | None:
        """Get a cached Keycloak token if still valid, else None."""
        if not (cached_token_info := storage.read()):
            return None
        if not isinstance(cached_token_info, CachedTokenInfo):
            storage.clear()
            return None
        try:
            access_token = self._decrypt_access_token(
                cached_token_info.token, cached_token_info.ttl
            )
        except InvalidToken:
            storage.clear()
            return None
        return KeycloakTokenInfo(access_token=access_token)

    def set(self, token_info: KeycloakTokenInfo, storage: Storage) -> None:
        """Store a Keycloak token in the cache."""
        fernet_token, time_to_live = self._encrypt_access_token(token_info.access_token)
        storage.write(CachedTokenInfo(token=fernet_token, ttl=time_to_live))


class AuthManagerTokenCache(BaseTokenCache):
    """Cache for auth-manager access tokens and persistent token ids."""

    def get(self, storage: Storage) -> AuthManagerTokenInfo | None:
        """Get a cached auth-manager token.

        Returns a valid access token when available. If the access token has expired
        but a persistent token id is stored, returns ``AuthManagerTokenInfo`` with an
        empty ``access_token`` so the caller can remint.
        """
        if not (cached_token_info := storage.read()):
            return None
        if not isinstance(cached_token_info, CachedAuthManagerTokenInfo):
            storage.clear()
            return None

        try:
            persistent_token_id = self._cipher.decrypt(
                cached_token_info.persistent_token_id
            ).decode()
        except InvalidToken:
            storage.clear()
            return None

        try:
            access_token = self._decrypt_access_token(
                cached_token_info.token, cached_token_info.ttl
            )
        except InvalidToken:
            return AuthManagerTokenInfo(access_token=None, persistent_token_id=persistent_token_id)

        return AuthManagerTokenInfo(
            access_token=access_token, persistent_token_id=persistent_token_id
        )

    def set(self, token_info: AuthManagerTokenInfo, storage: Storage) -> None:
        """Store an auth-manager token and persistent id in the cache."""
        if token_info.access_token is None:
            msg = "Cannot cache AuthManagerTokenInfo without an access_token"
            raise ValueError(msg)
        fernet_token, time_to_live = self._encrypt_access_token(token_info.access_token)
        persistent_token_id = self._cipher.encrypt(
            token_info.persistent_token_id.encode(encoding="utf-8")
        )
        storage.write(
            CachedAuthManagerTokenInfo(
                token=fernet_token,
                ttl=time_to_live,
                persistent_token_id=persistent_token_id,
            )
        )


def _now() -> int:
    """Return UTC timestamp now."""
    return int(time.time())


def _get_token_times(token: str) -> tuple[int, int]:
    """Get the creation time and time to live of a token."""
    info = jwt.decode(token.encode(), options={"verify_signature": False})
    effective_ttl = info["exp"] - info["iat"] - settings.EPSILON_TOKEN_TTL_SECONDS
    return info["iat"], effective_ttl
