"""Authorization flow module."""

import base64
import hashlib
import os
import re
import webbrowser

import httpx

from obi_auth.config import settings
from obi_auth.server import AuthServer


def _generate_pkce_pair():
    """Generate PKCE pair."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")
    return code_verifier, code_challenge


def _authorize(server: AuthServer, code_challenge: str, override_env: str | None) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "redirect_uri": server.redirect_uri,
        "scope": "openid",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "kc_idp_hint": "github",
    }

    base_auth_url = settings.get_keycloak_auth_endpoint(override_env=override_env)
    auth_url = f"{base_auth_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    webbrowser.open(auth_url)

    return server.wait_for_code()


def _exhange_code_for_token(
    code: str, redirect_uri: str, code_verifier: str, override_env: str | None
) -> str:
    response = httpx.post(
        url=settings.get_keycloak_token_endpoint(override_env=override_env),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    if response.status_code != 200:
        raise RuntimeError("Request failed.")

    access_token = response.json()["access_token"]

    return access_token


def pkce_authenticate(*, server: AuthServer, override_env: str | None = None) -> str:
    """Get access token using the PCKE authentication flow."""
    code_verifier, code_challenge = _generate_pkce_pair()
    code = _authorize(server, code_challenge, override_env)
    access_token = _exhange_code_for_token(code, server.redirect_uri, code_verifier, override_env)
    return access_token
