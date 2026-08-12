"""This module provides a simple HTTP server that listens for a Keycloak authorization code."""

import contextlib
import functools
import json
import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Self
from urllib.parse import parse_qs, urlparse

from obi_auth.config import settings
from obi_auth.exception import LocalServerError

L = logging.getLogger(__name__)
HOST = "localhost"
CALLBACK_PATH = "/callback"


@dataclass
class AuthState:
    """Class to manage authentication state."""

    code: str | None = None
    event: threading.Event = field(default_factory=threading.Event)


class _CallbackHandler(BaseHTTPRequestHandler):
    """Request handler extracting the authorization code out of the Keycloak redirect."""

    def __init__(self, *args, auth_state: AuthState, **kwargs) -> None:
        """Initialize the handler with the state to populate."""
        self.auth_state = auth_state
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        """Handle the Keycloak redirect and extract the authorization code."""
        url = urlparse(self.path)

        if url.path != CALLBACK_PATH:
            self._respond(HTTPStatus.NOT_FOUND, {"detail": "Not Found"})
            return

        codes = parse_qs(url.query).get("code")

        if not codes:
            self._respond(HTTPStatus.BAD_REQUEST, {"detail": "Authorization code not found"})
            return

        self.auth_state.code = codes[0]
        self.auth_state.event.set()  # Signal that we received the code

        self._respond(
            HTTPStatus.OK, {"message": "Authentication successful. You can close this window."}
        )

    def _respond(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        """Write a JSON response with the given status code."""
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Redirect the request logs to this module's logger instead of stderr."""
        L.debug("%s - %s", self.address_string(), format % args)


class AuthServer:
    """Class to manage authentication state."""

    def __init__(self):
        """Initialize authentication server."""
        self.auth_state = AuthState()
        self.port = None

    @property
    def redirect_uri(self) -> str:
        """Return redirect uril for server callback."""
        if not self.port:
            raise LocalServerError("Server has no port assigned.")
        return f"http://{HOST}:{self.port}{CALLBACK_PATH}"

    @contextlib.contextmanager
    def run(self) -> Iterator[Self]:
        """Start server in a background thread on an OS-assigned port.

        The server binds once to port ``0`` so the kernel picks a free port on the
        listening socket itself. This avoids the TOCTOU race of probing for a free
        port, releasing it, then binding again.
        """
        handler = functools.partial(_CallbackHandler, auth_state=self.auth_state)
        try:
            server = ThreadingHTTPServer((HOST, 0), handler)
        except OSError as e:
            raise LocalServerError(f"Failed to listen on {HOST}") from e

        self.port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        try:
            thread.start()
            L.info("Local server listening on http://%s:%s", HOST, self.port)
            yield self
        finally:
            L.debug("Stopping the local server")
            server.shutdown()
            thread.join(timeout=1)
            server.server_close()

    def wait_for_code(self, timeout: int = settings.LOCAL_SERVER_TIMEOUT) -> str:
        """Wait for code."""
        if self.auth_state.event.wait(timeout):
            self.auth_state.event.clear()
            if self.auth_state.code is None:
                raise LocalServerError("Authorization code was not set")
            return self.auth_state.code
        raise LocalServerError("Timeout waiting for authorization code")
