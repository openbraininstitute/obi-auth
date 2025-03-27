"""This module provides a client for the obi_auth service."""
import logging

from obi_auth.flow import pkce_authenticate
from obi_auth.server import AuthServer
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)

def get_token(*, environment: DeploymentEnvironment | None = None) -> str | None:
    """Get token."""
    try:
        with AuthServer().run() as local_server:
            return pkce_authenticate(server=local_server, override_env=environment)
    except TimeoutError as ex:
        L.warning("Error: %s", ex)
