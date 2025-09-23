"""This module provides typedefs for the obi_auth service."""

from enum import StrEnum, auto

from pydantic import BaseModel


class DeploymentEnvironment(StrEnum):
    """Deployment environment."""

    staging = auto()
    production = auto()


class KeycloakRealm(StrEnum):
    """Keycloak realms."""

    sbo = "SBO"


class TokenInfo(BaseModel):
    """Token information."""

    token: bytes
    ttl: int


class AuthMode(StrEnum):
    """Authentication models."""

    pkce = auto()
    daf = auto()


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
