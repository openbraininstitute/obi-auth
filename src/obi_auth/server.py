"""This module provides a simple HTTP server that listens for a Keycloak authorization code."""

import contextlib
import logging
import socket
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from obi_auth.config import settings
from obi_auth.exception import LocalServerError

L = logging.getLogger(__name__)
HOST = "localhost"


@dataclass
class AuthState:
    """Class to manage authentication state."""

    code: str | None = None
    event: threading.Event = threading.Event()


class AuthServer:
    """Class to manage authentication state."""

    def __init__(self):
        """Initialize authentication server."""
        self.app = FastAPI()
        self.auth_state = AuthState()
        self.port = None

        @self.app.get("/callback")
        def callback(request: Request):
            """Handle the Keycloak redirect and extracts the authorization code."""
            code = request.query_params.get("code")

            if not code:
                raise HTTPException(status_code=400, detail="Authorization code not found")

            self.auth_state.code = code
            self.auth_state.event.set()  # Signal that we received the code

            return {"message": "Authentication successful. You can close this window."}

    @property
    def redirect_uri(self) -> str:
        """Return redirect uril for server callback."""
        if not self.port:
            raise LocalServerError("Server has no port assigned.")
        return f"http://{HOST}:{self.port}/callback"

    @staticmethod
    def _find_free_port() -> int:
        """Bind to port 0 to let the OS select a free port, then return that port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @contextlib.contextmanager
    def run(self) -> Iterator[Self]:
        """Start server in a background thread."""
        self.port = self._find_free_port()
        config = uvicorn.Config(app=self.app, port=self.port, host=HOST, log_level="error")
        server = uvicorn.Server(config=config)
        thread = threading.Thread(target=server.run, daemon=True)
        try:
            thread.start()
            L.info("Local server listening on http://%s:%s", HOST, self.port)
            yield self
        finally:
            L.debug("Stopping the local server")
            server.should_exit = True
            thread.join(timeout=1)

    def wait_for_code(self, timeout: int = settings.LOCAL_SERVER_TIMEOUT) -> str:
        """Wait for code."""
        if self.auth_state.event.wait(timeout):
            self.auth_state.event.clear()
            return self.auth_state.code
        raise LocalServerError("Timeout waiting for authorization code")
