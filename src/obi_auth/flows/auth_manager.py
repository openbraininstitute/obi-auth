"""Authentication helpers for auth-manager persistent tokens."""

import logging

import httpx2

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import (
    AuthManagerTokenInfo,
    DeploymentEnvironment,
    KeycloakTokenInfo,
)

L = logging.getLogger(__name__)


def auth_manager_mint_access_token(
    persistent_token_id: str, *, environment: DeploymentEnvironment
) -> AuthManagerTokenInfo:
    """Mint an auth-manager access token from a persistent token id."""
    mint_data = (
        httpx2.post(
            url=settings.get_auth_manager_access_token_endpoint(override_env=environment),
            headers={"id": persistent_token_id},
        )
        .raise_for_status()
        .json()
    )

    if not (access_token := mint_data.get("data", {}).get("access_token")):
        msg = f"AuthManager unexpected payload: {mint_data}"
        L.error(msg)
        raise AuthFlowError(msg)

    return AuthManagerTokenInfo(access_token=access_token, persistent_token_id=persistent_token_id)


def auth_manager_exchange_token(
    token_info: KeycloakTokenInfo, *, environment: DeploymentEnvironment
) -> AuthManagerTokenInfo:
    """Exchange a Keycloak access token and mint an auth-manager access token."""
    exchange_data = (
        httpx2.post(
            url=settings.get_auth_manager_token_exchange_endpoint(override_env=environment),
            headers={"Authorization": f"Bearer {token_info.access_token}"},
        )
        .raise_for_status()
        .json()
    )

    if not (token_id := exchange_data.get("data", {}).get("id")):
        msg = f"AuthManager unexpected payload: {exchange_data}"
        L.error(msg)
        raise AuthFlowError(msg)

    return auth_manager_mint_access_token(token_id, environment=environment)
