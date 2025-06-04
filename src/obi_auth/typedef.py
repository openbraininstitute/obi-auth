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
