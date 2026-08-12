import pytest

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.flows import auth_manager as test_module
from obi_auth.typedef import AuthManagerTokenInfo, KeycloakTokenInfo


def test_auth_manager_mint_access_token(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {"access_token": "minted-token"}})
    res = test_module.auth_manager_mint_access_token("persistent-id", environment="staging")
    assert res == AuthManagerTokenInfo(
        access_token="minted-token",  # noqa: S106
        persistent_token_id="persistent-id",  # noqa: S106
    )
    assert httpx2_mock.calls[0].request.headers["id"] == "persistent-id"


def test_auth_manager_mint_access_token__raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(
        AuthFlowError, match=r"AuthManager unexpected payload: \{'data': \{\}\}"
    ) as exc_info:
        test_module.auth_manager_mint_access_token("persistent-id", environment="staging")
    assert isinstance(exc_info.value.args[0], str)


def test_auth_manager_exchange_token(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {"id": "exchanged-id"}})
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {"access_token": "minted-token"}})

    res = test_module.auth_manager_exchange_token(
        KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
        environment="staging",
    )
    assert res == AuthManagerTokenInfo(
        access_token="minted-token",  # noqa: S106
        persistent_token_id="exchanged-id",  # noqa: S106
    )
    requests = [call.request for call in httpx2_mock.calls]
    assert requests[0].headers["Authorization"] == "Bearer public-token"
    assert requests[1].headers["id"] == "exchanged-id"


def test_auth_manager_exchange_token__exchange_raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(
        AuthFlowError, match=r"AuthManager unexpected payload: \{'data': \{\}\}"
    ) as exc_info:
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )
    assert isinstance(exc_info.value.args[0], str)


def test_auth_manager_exchange_token__mint_raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {"id": "exchanged-id"}})
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )
