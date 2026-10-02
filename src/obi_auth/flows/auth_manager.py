"""Authentication helpers for auth-manager persistent tokens."""

import logging
import sys
import webbrowser
from time import monotonic, sleep
from typing import TypedDict

import httpx2

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import (
    AuthManagerTokenInfo,
    DeploymentEnvironment,
    KeycloakTokenInfo,
)
from obi_auth.util import is_running_in_notebook

L = logging.getLogger(__name__)


class OfflineConsentMessageData(TypedDict):
    """Data structure for offline consent message content."""

    title: str
    steps: list[str]
    url: str


_OFFLINE_CONSENT_MESSAGE: OfflineConsentMessageData = {
    "title": "Offline Access Consent Required\n\n",
    "steps": [
        "1. Open the consent URL below\n",
        "2. Grant offline access in the browser\n",
        "3. Return here when done\n\n",
    ],
    "url": "Consent URL:\n",
}


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


def _auth_manager_exchange_persistent_id(
    token_info: KeycloakTokenInfo, *, environment: DeploymentEnvironment
) -> str:
    """Exchange a Keycloak access token for a session vault persistent id."""
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

    return str(token_id)


def auth_manager_exchange_token(
    token_info: KeycloakTokenInfo, *, environment: DeploymentEnvironment
) -> AuthManagerTokenInfo:
    """Exchange a Keycloak access token and mint an auth-manager access token."""
    token_id = _auth_manager_exchange_persistent_id(token_info, environment=environment)
    return auth_manager_mint_access_token(token_id, environment=environment)


def auth_manager_upgrade_to_offline_token(
    token_info: AuthManagerTokenInfo, *, environment: DeploymentEnvironment
) -> AuthManagerTokenInfo:
    """Upgrade a session vault access token to an offline vault token (consent if needed)."""
    if token_info.access_token is None:
        raise AuthFlowError("AuthManager exchange did not return an access token")

    offline_id = auth_manager_get_offline_token_id(token_info.access_token, environment=environment)
    if offline_id is None:
        offline_id = auth_manager_request_and_await_offline_consent(
            token_info.access_token, environment=environment
        )

    return auth_manager_mint_access_token(offline_id, environment=environment)


def auth_manager_get_offline_token_id(
    access_token: str, *, environment: DeploymentEnvironment
) -> str | None:
    """Return an offline persistent id for this session, or None if none exists yet."""
    response = httpx2.post(
        url=settings.get_auth_manager_offline_token_id_endpoint(override_env=environment),
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    token_id = data.get("data", {}).get("persistent_token_id")
    if not token_id:
        msg = f"AuthManager unexpected payload: {data}"
        L.error(msg)
        raise AuthFlowError(msg)
    return str(token_id)


def auth_manager_request_offline_consent(
    access_token: str, *, environment: DeploymentEnvironment
) -> str:
    """Start offline consent and return the Keycloak consent URL."""
    data = (
        httpx2.get(
            url=settings.get_auth_manager_offline_token_endpoint(override_env=environment),
            headers={"Authorization": f"Bearer {access_token}"},
        )
        .raise_for_status()
        .json()
    )
    if not (consent_url := data.get("data", {}).get("consent_url")):
        msg = f"AuthManager unexpected payload: {data}"
        L.error(msg)
        raise AuthFlowError(msg)
    return consent_url


def auth_manager_request_and_await_offline_consent(
    access_token: str, *, environment: DeploymentEnvironment
) -> str:
    """Prompt for offline consent and poll until an offline vault id is available."""
    consent_url = auth_manager_request_offline_consent(access_token, environment=environment)
    _display_offline_consent_prompt(consent_url)
    webbrowser.open(consent_url)

    deadline = monotonic() + settings.OFFLINE_CONSENT_TIMEOUT_SECONDS
    while monotonic() < deadline:
        if offline_id := auth_manager_get_offline_token_id(access_token, environment=environment):
            print("\r   ✓ Offline access granted!", flush=True, file=sys.stderr)
            return offline_id
        sleep(settings.OFFLINE_CONSENT_POLL_INTERVAL_SECONDS)

    print("\r   ✗ Offline consent timed out", flush=True, file=sys.stderr)
    raise AuthFlowError("Offline consent timed out waiting for user approval.")


def _display_offline_consent_prompt(consent_url: str) -> None:
    """Show the offline consent URL on stderr (keep stdout token-only for piping)."""
    if is_running_in_notebook():
        try:
            from rich.console import Console
            from rich.style import Style
            from rich.text import Text

            auth_text = Text()
            auth_text.append(_OFFLINE_CONSENT_MESSAGE["title"], style="bold deep_sky_blue4")
            for step in _OFFLINE_CONSENT_MESSAGE["steps"]:
                auth_text.append(step, style="white")
            auth_text.append(_OFFLINE_CONSENT_MESSAGE["url"], style="dim")
            link_style = Style(color="deep_sky_blue4", underline=True, link=consent_url)
            auth_text.append(consent_url, style=link_style)
            Console(stderr=True).print(auth_text)
            return
        except Exception as e:
            L.warning("Rich is not supported, using fallback: %s", e)

    print(_OFFLINE_CONSENT_MESSAGE["title"], file=sys.stderr)
    for step in _OFFLINE_CONSENT_MESSAGE["steps"]:
        print(step, file=sys.stderr)
    print(_OFFLINE_CONSENT_MESSAGE["url"], file=sys.stderr)
    print(f"   {consent_url}", file=sys.stderr)
