"""This module provides a client for the obi_auth service."""

import logging
from collections.abc import Callable

import jwt

from obi_auth.cache import AuthManagerTokenCache, TokenCache
from obi_auth.config import settings
from obi_auth.exception import AuthFlowError, ClientError, ConfigError, LocalServerError
from obi_auth.flows.auth_manager import (
    auth_manager_exchange_token,
    auth_manager_mint_access_token,
)
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
_AUTH_MANAGER_TOKEN_CACHE = AuthManagerTokenCache()


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

    if token_provider == TokenProvider.auth_manager:
        return _get_auth_manager_token(
            storage=storage,
            environment=environment,
            auth_mode=auth_mode,
            force_refresh=force_refresh,
        )
    return _get_keycloak_token(
        storage=storage,
        environment=environment,
        auth_mode=auth_mode,
        force_refresh=force_refresh,
    )


def _get_keycloak_token(
    *,
    storage: Storage,
    environment: DeploymentEnvironment,
    auth_mode: AuthMode,
    force_refresh: bool,
) -> str:
    if force_refresh:
        L.debug("Forcing token refresh, clearing cached token")
        storage.clear()
    elif token_info := _TOKEN_CACHE.get(storage):
        L.debug("Using cached token")
        return token_info.access_token

    auth_method = _get_auth_method(auth_mode)
    token_info = auth_method(environment=environment)
    _TOKEN_CACHE.set(token_info, storage)
    return token_info.access_token


def _get_auth_manager_token(
    *,
    storage: Storage,
    environment: DeploymentEnvironment,
    auth_mode: AuthMode,
    force_refresh: bool,
) -> str:
    if force_refresh:
        L.debug("Forcing token refresh, clearing cached token")
        storage.clear()
    elif token_info := _AUTH_MANAGER_TOKEN_CACHE.get(storage):
        if token_info.access_token:
            L.debug("Using cached token")
            return token_info.access_token
        if refreshed := _refresh_auth_manager_token(
            token_info.persistent_token_id, storage=storage, environment=environment
        ):
            if refreshed.access_token is None:
                raise ClientError("Authentication process failed.")
            return refreshed.access_token

    auth_method = _get_auth_method(auth_mode)
    keycloak_token = auth_method(environment=environment)
    try:
        token_info = auth_manager_exchange_token(keycloak_token, environment=environment)
    except AuthFlowError as e:
        raise ClientError("Authentication process failed.") from e

    _AUTH_MANAGER_TOKEN_CACHE.set(token_info, storage)
    if token_info.access_token is None:
        raise ClientError("Authentication process failed.")
    return token_info.access_token


def _refresh_auth_manager_token(
    persistent_token_id: str, *, storage: Storage, environment: DeploymentEnvironment
) -> AuthManagerTokenInfo | None:
    """Mint a new access token from a cached persistent token id."""
    L.debug("Cached access token expired, minting a new one from persistent token id")
    try:
        token_info = auth_manager_mint_access_token(persistent_token_id, environment=environment)
    except AuthFlowError:
        L.debug("Failed to mint access token from persistent token id, clearing cache")
        storage.clear()
        return None

    _AUTH_MANAGER_TOKEN_CACHE.set(token_info, storage)
    return token_info


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
