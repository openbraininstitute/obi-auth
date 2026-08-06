"""This module provides typedefs for the obi_auth service."""

from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class DeploymentEnvironment(StrEnum):
    """Deployment environment."""

    staging = auto()
    production = auto()


class KeycloakRealm(StrEnum):
    """Keycloak realms."""

    sbo = "SBO"


class CachedTokenInfo(BaseModel):
    """Encrypted Keycloak token stored on disk."""

    token: bytes
    ttl: int


class CachedAuthManagerTokenInfo(BaseModel):
    """Encrypted auth-manager token and persistent id stored on disk."""

    token: bytes
    ttl: int
    persistent_token_id: bytes


class AuthMode(StrEnum):
    """Authentication methods for obtaining credentials."""

    pkce = auto()
    daf = auto()
    # Public API: mint via auth-manager from an existing persistent token id
    # (no Keycloak login). Backwards-compatible with pre-token-exchange callers.
    persistent_token = auto()


class TokenProvider(StrEnum):
    """Issuer of the access token returned by ``get_token``."""

    keycloak = auto()
    auth_manager = auto()


class KeycloakTokenInfo(BaseModel):
    """Keycloak access token."""

    token_provider: Literal[TokenProvider.keycloak] = TokenProvider.keycloak
    access_token: str


class AuthManagerTokenInfo(BaseModel):
    """Auth-manager access token and associated persistent token id."""

    token_provider: Literal[TokenProvider.auth_manager] = TokenProvider.auth_manager
    access_token: str | None
    persistent_token_id: str


TokenInfo = Annotated[
    KeycloakTokenInfo | AuthManagerTokenInfo,
    Field(discriminator="token_provider"),
]


class AuthDeviceInfo(BaseModel):
    """Model for auth payload returned by keycloak device auth flow."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int

    @property
    def max_retries(self) -> int:
        """Return max retries from expiration time and polling interval."""
        return self.expires_in // self.interval
