"""This module provides a simple HTTP server that listens for a Keycloak authorization code."""

import base64
import hashlib
import os
import re
import socket
import threading
import webbrowser
from time import sleep

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request

from obi_auth.config import settings

HOST = "localhost"

app = FastAPI()
auth_code = None


@app.get("/callback")
async def callback(request: Request):
    """Handles the Keycloak redirect and extracts the authorization code."""
    global auth_code

    code = request.query_params.get("code")
    # state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    auth_code = code

    return {"message": "Authentication successful. You can close this window."}


def _find_free_port() -> int:
    """Bind to port 0 to let the OS select a free port, then return that port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def auth_server():
    """Run a auth server."""
    port = _find_free_port()
    config = uvicorn.Config(app=app, port=port, host=HOST, log_level="error")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run)
    thread.start()
    return f"http://{HOST}:{port}"  # Provide the dynamically allocated port to the caller
    # try:
    #    yield f"http://{HOST}:{port}"  # Provide the dynamically allocated port to the caller
    # finally:
    #    print()
    #    #shutdown_server()  # Cleanup: Ensure server shutdown after use


def generate_pkce_pair():
    """Generate PCKE pair."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")
    return code_verifier, code_challenge


def authenticate_with_keycloak(*, override_env: str | None = None):
    """Authenticate with Keycloak and return the authorization code."""
    # Start the authentication server on a free port
    global auth_code

    url = auth_server()
    redirect_uri = f"{url}/callback"
    print(f"Authentication server running on {redirect_uri}")

    code_verifier, code_challenge = generate_pkce_pair()

    params = {
        "response_type": "code",
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "kc_idp_hint": "github",
    }

    base_auth_url = settings.get_keycloak_auth_endpoint(override_env=override_env)
    auth_url = f"{base_auth_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    webbrowser.open(auth_url)

    # TODO: Add timeout
    while not (result := auth_code):
        sleep(0.1)

    response = httpx.post(
        url=settings.get_keycloak_token_endpoint(override_env=override_env),
        data={
            "grant_type": "authorization_code",
            "code": result,
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    if response.status_code != 200:
        raise RuntimeError("Request failed.")

    access_token = response.json()["access_token"]

    return access_token
