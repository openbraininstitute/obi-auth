"""This module provides typedefs for the obi_auth service."""

from enum import StrEnum

from pydantic import BaseModel


class DeploymentEnvironment(StrEnum):
    """Deployment environment."""

    staging = "staging"
    production = "production"


class KeycloakRealm(StrEnum):
    """Keycloak realms."""

    sbo = "SBO"


class TokenInfo(BaseModel):
    """Token information."""

    token: bytes
    ttl: int
