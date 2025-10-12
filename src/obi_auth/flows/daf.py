"""Authorization flow module."""

import logging
from time import sleep
from typing import TypedDict

import httpx

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import AuthDeviceInfo, DeploymentEnvironment
from obi_auth.util import is_running_in_notebook

L = logging.getLogger(__name__)


class AuthMessageData(TypedDict):
    """Data structure for authentication message content."""

    title: str
    steps: list[str]
    url: str


AUTHENTICATION_MESSAGE_DATA: AuthMessageData = {
    "title": "Device Authentication Required\n\n",
    "steps": [
        "1. Click on authentication URL\n",
        "2. Complete authentication in browser\n",
        "3. Return here when done\n\n",
    ],
    "url": "Authentication URL:\n",
}


def daf_authenticate(*, environment: DeploymentEnvironment) -> str:
    """Get access token using Device Authentication Flow."""
    device_info = _get_device_url_code(environment=environment)

    # Display user-friendly authentication prompt
    _display_auth_prompt(device_info)

    if token := _poll_device_code_token(device_info, environment):
        print("\r   ✓ Authentication completed successfully!", flush=True)
        return token

    print("\r   ✗ Authentication failed - timeout reached", flush=True)
    raise AuthFlowError("Polling using device code reached max retries.")


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


def _poll_device_code_token(
    device_info: AuthDeviceInfo, environment: DeploymentEnvironment
) -> str | None:
    for _ in range(device_info.max_retries):
        if token := _get_device_code_token(device_info, environment):
            return token
        sleep(device_info.interval)
    return None


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


def _display_auth_prompt(device_info: AuthDeviceInfo) -> None:
    """Display a user-friendly authentication prompt."""
    if is_running_in_notebook():
        L.debug("Using notebook authentication prompt")
        _display_notebook_auth_prompt(device_info)
    else:
        L.debug("Using terminal authentication prompt")
        _display_terminal_auth_prompt(device_info)


def _display_notebook_auth_prompt(device_info: AuthDeviceInfo) -> None:
    """Display a minimal authentication prompt for notebooks."""
    try:
        from rich.console import Console
        from rich.style import Style
        from rich.text import Text

        auth_text = Text()
        auth_text.append(AUTHENTICATION_MESSAGE_DATA["title"], style="bold blue")

        for step in AUTHENTICATION_MESSAGE_DATA["steps"]:
            auth_text.append(step, style="white")

        auth_text.append(AUTHENTICATION_MESSAGE_DATA["url"], style="dim")

        verification_url = device_info.verification_uri_complete
        link_style = Style(color="blue", underline=True, link=verification_url)
        auth_text.append(f"{verification_url}", style=link_style)

        Console().print(auth_text)

    except Exception as e:
        L.warning(f"Rich is not supported, using fallback: {e}")
        _display_terminal_auth_prompt(device_info)


def _display_terminal_auth_prompt(device_info: AuthDeviceInfo) -> None:
    """Display a simple authentication prompt for terminal usage."""
    print(AUTHENTICATION_MESSAGE_DATA["title"])

    for step in AUTHENTICATION_MESSAGE_DATA["steps"]:
        print(step)

    print(AUTHENTICATION_MESSAGE_DATA["url"])
    print(f"   {device_info.verification_uri_complete}")
