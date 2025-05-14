"""This module provides a client for the obi_auth service."""

import logging

from obi_auth.cache import TokenCache
from obi_auth.config import settings
from obi_auth.exception import AuthFlowError, ClientError, ConfigError, LocalServerError
from obi_auth.flow import pkce_authenticate
from obi_auth.server import AuthServer
from obi_auth.storage import Storage
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)


_TOKEN_CACHE = TokenCache()


def get_token(*, environment: DeploymentEnvironment = DeploymentEnvironment.staging) -> str | None:
    """Get token."""
    L.debug("Using %s as the config dir", settings.config_dir)
    storage = Storage(config_dir=settings.config_dir, environment=environment)

    if token := _TOKEN_CACHE.get(storage):
        L.debug("Using cached token")
        return token

    try:
        with AuthServer().run() as local_server:
            token = pkce_authenticate(server=local_server, override_env=environment)
            _TOKEN_CACHE.set(token, storage)
            return token
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e
    except LocalServerError as e:
        raise ClientError("Local server failed to authenticate.") from e
    except ConfigError as e:
        raise ClientError("There is a mistake with configuration settings.") from e
