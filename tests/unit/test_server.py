from obi_auth import server as test_module
from obi_auth.server import AuthServer


def test_server():
    auth_server = test_module.AuthServer()
    assert isinstance(auth_server, AuthServer)
