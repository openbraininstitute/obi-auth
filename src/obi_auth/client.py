"""This module provides a client for the obi_auth service."""

import logging

from obi_auth.exception import AuthFlowError, ClientError, ConfigError, LocalServerError
from obi_auth.flow import pkce_authenticate
from obi_auth.server import AuthServer
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)


def get_token(*, environment: DeploymentEnvironment | None = None) -> str | None:
    """Get token."""
    try:
        with AuthServer().run() as local_server:
            return pkce_authenticate(server=local_server, override_env=environment)
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e
    except LocalServerError as e:
        raise ClientError("Local server failed to authenticate.") from e
    except ConfigError as e:
        raise ClientError("There is a mistake with configuration settings.") from e
