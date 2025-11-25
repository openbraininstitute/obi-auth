"""Authentication flow using a persistent token id and auth-manager."""

import logging

import httpx

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)


def persistent_token_authenticate(
    *, environment: DeploymentEnvironment, persistent_token_id: str
) -> str:
    """Get access token using a persistent token id."""
    data = (
        httpx.post(
            url=settings.get_auth_manager_access_token_endpoint(override_env=environment),
            headers={"id": persistent_token_id},
        )
        .raise_for_status()
        .json()
    )

    if access_token := data.get("data", {}).get("access_token"):
        return access_token

    msg = "AuthManager unexpected payload: {}", data
    L.error(msg)
    raise AuthFlowError(msg)
