"""Authorization flow module."""

import logging
from time import sleep

import httpx

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)


def daf_authenticate(*, environment: DeploymentEnvironment) -> str:
    """Get access token using Device Authentication Flow."""
    verification_url, device_code = _get_device_url_code(environment=environment)

    print("Please open url in a different tab: ", verification_url)

    return _poll_device_code_token(
        device_code,
        environment,
        interval=settings.POLLING_INTERVAL,
        max_retries=settings.POLLING_MAX_RETRIES,
    )


def _get_device_url_code(
    *,
    environment: DeploymentEnvironment,
) -> tuple[str, str]:
    url = settings.get_keycloak_device_auth_endpoint(environment)
    response = httpx.post(
        url=url,
        data={
            "client_id": settings.KEYCLOAK_CLIENT_ID,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["verification_uri_complete"], data["device_code"]


def _poll_device_code_token(device_code, environment, interval: int, max_retries: int) -> str:
    for _ in range(max_retries):
        try:
            return _get_device_code_token(device_code, environment)
        except httpx.HTTPStatusError:
            sleep(interval)

    raise AuthFlowError("Polling using device code reached max retries.")


def _get_device_code_token(device_code: str, environment: DeploymentEnvironment) -> str:
    url = settings.get_keycloak_token_endpoint(environment)
    response = httpx.post(
        url=url,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "device_code": device_code,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]
