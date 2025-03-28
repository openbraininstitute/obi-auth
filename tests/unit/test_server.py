import httpx
import pytest

from obi_auth import server as test_module
from obi_auth.exception import LocalServerError
from obi_auth.server import AuthServer


@pytest.fixture
def server():
    return test_module.AuthServer()


@pytest.fixture
def running_server(server):
    with server.run() as local_server:
        yield local_server


def test_server(server):
    assert isinstance(server, AuthServer)


def test_find_free_port():
    assert AuthServer._find_free_port() > 0


def test_redirect_uri(server):
    with pytest.raises(LocalServerError, match="Server has no port assigned."):
        _ = server.redirect_uri
    server.port = "8000"
    assert server.redirect_uri == f"http://localhost:{server.port}/callback"


def test_wait_for_code(running_server):
    with pytest.raises(LocalServerError, match="Timeout waiting for authorization code"):
        running_server.wait_for_code(timeout=0.1)

    response = httpx.get(f"{running_server.redirect_uri}")
    assert response.status_code == 400

    response = httpx.get(f"{running_server.redirect_uri}?code=mock-code")
    response.raise_for_status()

    res = running_server.wait_for_code()
    assert res == "mock-code"
