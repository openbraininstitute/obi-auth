"""This module provides a client for the obi_auth service."""

import logging
from collections.abc import Callable

import jwt

from obi_auth.cache import TokenCache
from obi_auth.config import settings
from obi_auth.exception import AuthFlowError, ClientError, ConfigError, LocalServerError
from obi_auth.flows.auth_manager import auth_manager_exchange_token
from obi_auth.flows.daf import daf_authenticate
from obi_auth.flows.pkce import pkce_authenticate
from obi_auth.request import user_info
from obi_auth.server import AuthServer
from obi_auth.storage import Storage
from obi_auth.typedef import (
    AuthManagerTokenInfo,
    AuthMode,
    DeploymentEnvironment,
    KeycloakTokenInfo,
    TokenProvider,
)

L = logging.getLogger(__name__)


_TOKEN_CACHE = TokenCache()


def get_token(
    *,
    environment: DeploymentEnvironment = DeploymentEnvironment.staging,
    auth_mode: AuthMode = AuthMode.pkce,
    token_provider: TokenProvider = TokenProvider.keycloak,
    force_refresh: bool = False,
) -> str:
    """Get token.

    Args:
        environment: Target deployment environment.
        auth_mode: How to authenticate with Keycloak (``pkce`` or ``daf``).
        token_provider: Who issues the returned access token. ``keycloak`` returns
            the Keycloak token directly; ``auth_manager`` exchanges it for a
            persistent token and mints an auth-manager access token.
        force_refresh: Clear the cached token and authenticate again.
    """
    auth_mode = AuthMode(auth_mode)
    token_provider = TokenProvider(token_provider)

    L.debug("Using %s as the config dir", settings.config_dir)
    storage = Storage(
        config_dir=settings.config_dir,
        environment=environment,
        key=f"{auth_mode}_{token_provider}",
    )

    if force_refresh:
        L.debug("Forcing token refresh, clearing cached token")
        storage.clear()
    elif token_info := _TOKEN_CACHE.get(storage):
        L.debug("Using cached token")
        return token_info.access_token

    auth_method = _get_auth_method(auth_mode)
    token_info: KeycloakTokenInfo = auth_method(environment=environment)

    if token_provider == TokenProvider.auth_manager:
        try:
            token_info: AuthManagerTokenInfo = auth_manager_exchange_token(
                token_info, environment=environment
            )
        except AuthFlowError as e:
            raise ClientError("Authentication process failed.") from e

    _TOKEN_CACHE.set(token_info, storage)

    return token_info.access_token


def _get_auth_method(auth_mode: AuthMode) -> Callable[..., KeycloakTokenInfo]:
    methods: dict[AuthMode, Callable[..., KeycloakTokenInfo]] = {
        AuthMode.pkce: _pkce_authenticate,
        AuthMode.daf: _daf_authenticate,
    }
    return methods[auth_mode]


def _pkce_authenticate(*, environment: DeploymentEnvironment) -> KeycloakTokenInfo:
    try:
        with AuthServer().run() as local_server:
            return pkce_authenticate(server=local_server, environment=environment)
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e
    except LocalServerError as e:
        raise ClientError("Local server failed to authenticate.") from e
    except ConfigError as e:
        raise ClientError("There is a mistake with configuration settings.") from e


def _daf_authenticate(*, environment: DeploymentEnvironment) -> KeycloakTokenInfo:
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
