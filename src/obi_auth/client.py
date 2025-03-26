"""This module provides a client for the obi_auth service."""

from obi_auth.flow import pkce_authenticate
from obi_auth.server import AuthServer
from obi_auth.typedef import DeploymentEnvironment


def get_token(*, environment: DeploymentEnvironment | None = None):
    """Get token."""
    local_server = AuthServer()
    local_server.start()
    access_token = pkce_authenticate(server=local_server, override_env=environment)
    return access_token
