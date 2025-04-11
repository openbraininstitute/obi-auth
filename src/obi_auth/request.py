"""Requests module."""

import httpx

from obi_auth.config import settings
from obi_auth.typedef import DeploymentEnvironment


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
