"""This module provides a client for the obi_auth service."""

import logging
from collections.abc import Callable

import jwt

from obi_auth.cache import TokenCache
from obi_auth.config import settings
from obi_auth.exception import AuthFlowError, ClientError, ConfigError, LocalServerError
from obi_auth.flows.daf import daf_authenticate
from obi_auth.flows.pkce import pkce_authenticate
from obi_auth.request import user_info
from obi_auth.server import AuthServer
from obi_auth.storage import Storage
from obi_auth.typedef import AuthMode, DeploymentEnvironment

L = logging.getLogger(__name__)


_TOKEN_CACHE = TokenCache()


def get_token(
    *,
    environment: DeploymentEnvironment = DeploymentEnvironment.staging,
    auth_mode: AuthMode = AuthMode.pkce,
) -> str | None:
    """Get token."""
    L.debug("Using %s as the config dir", settings.config_dir)
    storage = Storage(config_dir=settings.config_dir, environment=environment)

    if token := _TOKEN_CACHE.get(storage):
        L.debug("Using cached token")
        return token

    auth_method = _get_auth_method(auth_mode)

    token = auth_method(environment)

    _TOKEN_CACHE.set(token, storage)

    return token


def _get_auth_method(auth_mode: AuthMode) -> Callable:
    return {
        AuthMode.pkce: _pkce_authenticate,
        AuthMode.daf: _daf_authenticate,
    }[auth_mode]


def _pkce_authenticate(environment: DeploymentEnvironment) -> str:
    try:
        with AuthServer().run() as local_server:
            return pkce_authenticate(server=local_server, environment=environment)
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e
    except LocalServerError as e:
        raise ClientError("Local server failed to authenticate.") from e
    except ConfigError as e:
        raise ClientError("There is a mistake with configuration settings.") from e


def _daf_authenticate(environment: DeploymentEnvironment) -> str:
    try:
        return daf_authenticate(environment=environment)
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e


def get_token_info(token: str) -> dict:
    """Decode token information."""
    return jwt.decode(token, options={"verify_signature": False})


def get_user_info(
    token: str, environment: DeploymentEnvironment = DeploymentEnvironment.staging
) -> dict:
    """Get user info from valid token."""
    return user_info(token, environment=environment).json()
