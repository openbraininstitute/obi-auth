"""Authorization flow module."""

import base64
import hashlib
import logging
import os
import re
import secrets
import urllib.parse
import webbrowser

from obi_auth.config import settings
from obi_auth.request import exchange_code_for_token
from obi_auth.server import AuthServer
from obi_auth.typedef import DeploymentEnvironment, KeycloakTokenInfo

L = logging.getLogger(__name__)


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE pair."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")
    return code_verifier, code_challenge


def _generate_state() -> str:
    """Generate a cryptographically random OAuth state value."""
    return secrets.token_urlsafe(32)


def _build_auth_url(
    code_challenge: str,
    redirect_uri: str,
    state: str,
    override_env: DeploymentEnvironment | None,
) -> str:
    """Construct authentication url to open with a browser."""
    params = {
        "response_type": "code",
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "kc_idp_hint": "github",
    }

    base_auth_url = settings.get_keycloak_auth_endpoint(override_env=override_env)

    # Build the full URL
    encoded_params = urllib.parse.urlencode(params)
    return f"{base_auth_url}?{encoded_params}"


def _authorize(
    server: AuthServer, code_challenge: str, override_env: DeploymentEnvironment | None
) -> str:
    """Ask user to login in order to retrieve a code to exchange for a token."""
    state = _generate_state()
    server.expect_state(state)
    auth_url = _build_auth_url(code_challenge, server.redirect_uri, state, override_env)
    L.info("Opening browser for authentication")
    webbrowser.open(auth_url)
    return server.wait_for_code()


def _exchange_code_for_token(
    code: str, redirect_uri: str, code_verifier: str, override_env: DeploymentEnvironment | None
) -> str:
    response = exchange_code_for_token(
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        override_env=override_env,
    )
    return response.json()["access_token"]


def pkce_authenticate(
    *, server: AuthServer, environment: DeploymentEnvironment | None = None
) -> KeycloakTokenInfo:
    """Get access token using the PCKE authentication flow."""
    code_verifier, code_challenge = _generate_pkce_pair()
    code = _authorize(server, code_challenge, environment)
    access_token = _exchange_code_for_token(code, server.redirect_uri, code_verifier, environment)
    return KeycloakTokenInfo(access_token=access_token)
