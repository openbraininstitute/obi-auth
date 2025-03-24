"""This module provides typedefs for the obi_auth service."""

from enum import StrEnum


class DeploymentEnvironment(StrEnum):
    """Deployment environment."""

    staging = "staging"
    production = "poroduction"


class KeycloakRealm(StrEnum):
    """Keycloak realms."""

    sbo = "SBO"
