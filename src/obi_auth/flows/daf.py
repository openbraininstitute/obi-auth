"""Authorization flow module."""

import logging
from time import sleep

import httpx

from obi_auth.config import settings
from obi_auth.typedef import DeploymentEnvironment

L = logging.getLogger(__name__)


def daf_authenticate(*, environment: DeploymentEnvironment) -> str:
    """Get access token using Device Authentication Flow."""
    verification_url, device_code = _get_device_code_response(environment=environment)

    print("Please open url in a different tab: ", verification_url)

    return _poll_device_code_token(device_code, environment)


def _get_device_code_response(
    *,
    environment: DeploymentEnvironment,
):
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


def _poll_device_code_token(device_code, environment):
    while True:
        try:
            return _get_device_code_token(device_code, environment)
        except:
            pass

        sleep(1)


def _get_device_code_token(device_code: str, environment: DeploymentEnvironment):
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
