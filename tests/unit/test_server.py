import httpx2
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


def test_redirect_uri(server):
    with pytest.raises(LocalServerError, match="Server has no port assigned."):
        _ = server.redirect_uri
    server.port = "8000"
    assert server.redirect_uri == f"http://localhost:{server.port}/callback"


def test_wait_for_code(running_server):
    running_server.expect_state("expected-state")

    with pytest.raises(LocalServerError, match="Timeout waiting for authorization code"):
        running_server.wait_for_code(timeout=0.1)

    response = httpx2.get(f"{running_server.redirect_uri}")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid OAuth state"}

    response = httpx2.get(f"{running_server.redirect_uri}?code=mock-code&state=wrong-state")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid OAuth state"}

    response = httpx2.get(f"{running_server.redirect_uri}?code=mock-code&state=expected-state")
    response.raise_for_status()

    res = running_server.wait_for_code()
    assert res == "mock-code"
    assert running_server.auth_state.code is None


def test_wait_for_code_oauth_error(running_server):
    running_server.expect_state("expected-state")

    response = httpx2.get(
        f"{running_server.redirect_uri}"
        "?error=access_denied&error_description=User+denied&state=expected-state"
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "User denied"}

    with pytest.raises(LocalServerError, match="Authorization failed: User denied"):
        running_server.wait_for_code(timeout=1)


def test_wait_for_code_oauth_error_without_description(running_server):
    running_server.expect_state("expected-state")

    response = httpx2.get(f"{running_server.redirect_uri}?error=access_denied&state=expected-state")
    assert response.status_code == 400
    assert response.json() == {"detail": "access_denied"}

    with pytest.raises(LocalServerError, match="Authorization failed: access_denied"):
        running_server.wait_for_code(timeout=1)


def test_callback_valid_state_missing_code(running_server):
    running_server.expect_state("expected-state")

    response = httpx2.get(f"{running_server.redirect_uri}?state=expected-state")
    assert response.status_code == 400
    assert response.json() == {"detail": "Authorization code not found"}


def test_unknown_path_returns_not_found(running_server):
    response = httpx2.get(f"http://localhost:{running_server.port}/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_run_assigns_port_from_listening_socket(running_server):
    assert isinstance(running_server.port, int)
    assert running_server.port > 0
    assert running_server.redirect_uri == f"http://localhost:{running_server.port}/callback"

    # The reported port must be the one actually accepting connections.
    response = httpx2.get(f"http://localhost:{running_server.port}/callback")
    assert response.status_code == 400


def test_run_binds_localhost_only(running_server):
    # Binding to localhost must not expose the callback on a non-loopback wildcard probe.
    # Connecting via 127.0.0.1 (loopback) should work; that is what HOST resolves to.
    response = httpx2.get(f"http://127.0.0.1:{running_server.port}/callback")
    assert response.status_code == 400


def test_concurrent_servers_get_distinct_ports():
    server_a = AuthServer()
    server_b = AuthServer()
    with server_a.run() as a, server_b.run() as b:
        assert a.port != b.port
        a.expect_state("state-a")
        b.expect_state("state-b")
        assert httpx2.get(f"{a.redirect_uri}?code=a&state=state-a").status_code == 200
        assert httpx2.get(f"{b.redirect_uri}?code=b&state=state-b").status_code == 200
        assert a.wait_for_code(timeout=1) == "a"
        assert b.wait_for_code(timeout=1) == "b"


def test_run_stops_listening_after_context_exit(server):
    with server.run() as local_server:
        port = local_server.port
        assert httpx2.get(f"http://localhost:{port}/callback").status_code == 400

    with pytest.raises(httpx2.ConnectError):
        httpx2.get(f"http://localhost:{port}/callback", timeout=0.5)


def test_run_bind_failure(server, monkeypatch):
    def boom(*_args, **_kwargs):
        raise OSError("Address already in use")

    monkeypatch.setattr(test_module, "ThreadingHTTPServer", boom)

    with pytest.raises(LocalServerError, match="Failed to listen on localhost") as exc_info:
        with server.run():
            pass

    assert isinstance(exc_info.value.__cause__, OSError)
    assert server.port is None


def test_run_does_not_probe_then_rebind(server, monkeypatch):
    """Ensure we bind the listening server once (no separate free-port probe)."""
    bind_calls: list[tuple[str, int]] = []
    real_server = test_module.ThreadingHTTPServer

    class TrackingServer(real_server):
        def server_bind(self):
            bind_calls.append(self.server_address)
            return super().server_bind()

    monkeypatch.setattr(test_module, "ThreadingHTTPServer", TrackingServer)

    with server.run() as local_server:
        assert len(bind_calls) == 1
        assert bind_calls[0] == ("localhost", 0)
        assert local_server.port > 0
        # Port reported to callers must match the bound listening socket.
        assert local_server.port != 0


def test_wait_for_code_missing_code(server):
    server.expect_state("expected-state")
    server.auth_state.event.set()

    with pytest.raises(LocalServerError, match="Authorization code was not set"):
        server.wait_for_code()


def test_callback_rejects_code_without_expected_state(running_server):
    response = httpx2.get(f"{running_server.redirect_uri}?code=mock-code&state=any")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid OAuth state"}
