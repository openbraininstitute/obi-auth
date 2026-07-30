import pytest

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.flows import auth_manager as test_module
from obi_auth.typedef import AuthManagerTokenInfo, KeycloakTokenInfo


def test_auth_manager_exchange_token(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_token_exchange_endpoint(override_env="staging"),
        json={"data": {"id": "exchanged-id"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_access_token_endpoint(override_env="staging"),
        json={"data": {"access_token": "minted-token"}},
    )

    res = test_module.auth_manager_exchange_token(
        KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
        environment="staging",
    )
    assert res == AuthManagerTokenInfo(
        access_token="minted-token",  # noqa: S106
        persistent_token_id="exchanged-id",  # noqa: S106
    )
    requests = httpx_mock.get_requests()
    assert requests[0].headers["Authorization"] == "Bearer public-token"
    assert requests[1].headers["id"] == "exchanged-id"


def test_auth_manager_exchange_token__exchange_raises(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_token_exchange_endpoint(override_env="staging"),
        json={"data": {}},
    )
    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )


def test_auth_manager_exchange_token__mint_raises(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_token_exchange_endpoint(override_env="staging"),
        json={"data": {"id": "exchanged-id"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_access_token_endpoint(override_env="staging"),
        json={"data": {}},
    )
    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )
