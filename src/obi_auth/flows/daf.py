"""Authorization flow module."""

import logging
from time import sleep

import httpx

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import AuthDeviceInfo, DeploymentEnvironment

L = logging.getLogger(__name__)


def daf_authenticate(*, environment: DeploymentEnvironment) -> str:
    """Get access token using Device Authentication Flow."""
    device_info = _get_device_url_code(environment=environment)

    print("Please open url in a different tab: ", device_info.verification_uri_complete)

    return _poll_device_code_token(device_info=device_info, environment=environment)


def _get_device_url_code(
    *,
    environment: DeploymentEnvironment,
) -> AuthDeviceInfo:
    url = settings.get_keycloak_device_auth_endpoint(environment)
    response = httpx.post(
        url=url,
        data={
            "client_id": settings.KEYCLOAK_CLIENT_ID,
        },
    )
    response.raise_for_status()
    return AuthDeviceInfo.model_validate(response.json())


def _poll_device_code_token(device_info: AuthDeviceInfo, environment: DeploymentEnvironment) -> str:
    for _ in range(device_info.max_retries):
        if token := _get_device_code_token(device_info, environment):
            return token
        sleep(device_info.interval)
    raise AuthFlowError("Polling using device code reached max retries.")


def _get_device_code_token(
    device_info: AuthDeviceInfo, environment: DeploymentEnvironment
) -> str | None:
    url = settings.get_keycloak_token_endpoint(environment)
    response = httpx.post(
        url=url,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "device_code": device_info.device_code,
        },
    )
    if response.status_code == 400 and response.json()["error"] == "authorization_pending":
        return None
    response.raise_for_status()
    data = response.json()
    return data["access_token"]
