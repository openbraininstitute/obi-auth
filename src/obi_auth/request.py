"""Requests module."""

import logging

import httpx

from obi_auth.config import settings
from obi_auth.typedef import DeploymentEnvironment, PersistenceMode

L = logging.getLogger(__name__)


def exchange_code_for_token(
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    override_env: DeploymentEnvironment | None = None,
):
    """Exhange authentication code for acces token response."""
    url = settings.get_keycloak_token_endpoint(override_env)
    response = httpx.post(
        url=url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    response.raise_for_status()
    return response


def user_info(
    token: str,
    environment: DeploymentEnvironment | None = None,
):
    """Request user info with a valid token."""
    url = settings.get_keycloak_user_info_endpoint(environment)
    response = httpx.post(url, headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response


def get_persistent_token_id(
    access_token: str,
    persistence_mode: PersistenceMode = PersistenceMode.refresh,
    environment: DeploymentEnvironment | None = None,
) -> str:
    """Get a persistent token id with an access token."""
    auth_manager_url = settings.get_auth_manager_url(environment)

    mode_to_endpoint = {
        PersistenceMode.offline: f"{auth_manager_url}/offline-token-id",
        PersistenceMode.refresh: f"{auth_manager_url}/refresh-token-id",
    }

    js = (
        httpx.request(
            url=mode_to_endpoint[persistence_mode],
            method="POST",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        .raise_for_status()
        .json()
    )

    # refresh-token-id -> {"data": {"id": ...}}
    # offline-token-id -> {"data": {"persistent_token_id": ...}}
    if persistent_token_id := js.get("data", {}).get("id") or js.get("data", {}).get(
        "persistent_token_id"
    ):
        return persistent_token_id

    L.error("AuthManager unexpected payload: {}", js)
    raise RuntimeError(f"AuthManager unexpected payload: {js}")
