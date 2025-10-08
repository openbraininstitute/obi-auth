"""Token cache module."""

import json
import logging
import time

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken

from obi_auth.config import settings
from obi_auth.storage import Storage
from obi_auth.typedef import TokenInfo
from obi_auth.util import derive_fernet_key

L = logging.getLogger(__name__)


def _get_access_token(token: dict) -> dict | None:
    L.debug("Trying to use cached token")

    creation_time, time_to_live = _get_refresh_times(token["access_token"])
    if creation_time + time_to_live > int(time.time()):
        L.debug("`access_token` is still valid, returning it")
        return token

    creation_time, time_to_live = _get_refresh_times(token["refresh_token"])
    if creation_time + time_to_live > int(time.time()):
        L.debug("`refresh_token` is still valid, try to get a new refresh and access token")
        url = settings.get_keycloak_token_endpoint()
        resp = httpx.post(
            url,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "refresh_token": token["refresh_token"],
            },
        )
        return resp.json()

    return None


class TokenCache:
    """Token cache."""

    token_info: TokenInfo | None = None

    def __init__(self):
        """Initialize the token cache."""
        self._cipher = Fernet(key=derive_fernet_key())

    def get(self, storage: Storage) -> dict | None:
        """Get a cached token if valid, else None."""
        if not (token_info := storage.read()):
            return None
        try:
            token = json.loads(
                self._cipher.decrypt_at_time(
                    token=token_info.token,
                    ttl=token_info.ttl,
                    current_time=_now(),
                ).decode()
            )
            token = _get_access_token(token)
            if token is not None:
                self.set(token, storage)
            return token
        except InvalidToken:
            storage.clear()
            return None

    def set(self, token: dict, storage: Storage) -> None:
        """Store a new token in the cache."""
        creation_time, time_to_live = _get_refresh_times(token["refresh_token"])
        fernet_token: bytes = self._cipher.encrypt_at_time(
            data=json.dumps(token).encode(encoding="utf-8"),
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


def _get_refresh_times(token: str) -> tuple[int, int]:
    """Get the creation time and time to live of a token."""
    info = jwt.decode(token.encode(), options={"verify_signature": False})
    return info["iat"], info["exp"] - info["iat"]
