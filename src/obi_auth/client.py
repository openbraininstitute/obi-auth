"""This module provides a client for the obi_auth service."""

from obi_auth.auth_server import authenticate_with_keycloak
from obi_auth.typedef import DeploymentEnvironment


def get_token(*, environment: DeploymentEnvironment | None = None):
    """Get token."""
    code = authenticate_with_keycloak(override_env=environment)
    print(code)
