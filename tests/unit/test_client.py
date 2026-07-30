from unittest.mock import Mock, patch

import jwt
import pytest

from obi_auth import client as test_module
from obi_auth import exception
from obi_auth.typedef import AuthManagerTokenInfo, AuthMode, KeycloakTokenInfo, TokenProvider


@patch("obi_auth.client._get_auth_method")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token(mock_cache, mock_method):
    mock_cache.get.return_value = KeycloakTokenInfo(access_token="foo")  # noqa: S106
    assert test_module.get_token() == "foo"

    mock_cache.get.return_value = None

    mock_method.return_value = lambda *args, **kwargs: KeycloakTokenInfo(
        access_token="mock-token"  # noqa: S106
    )

    assert test_module.get_token() == "mock-token"


@patch(
    "obi_auth.client.auth_manager_exchange_token",
    return_value=AuthManagerTokenInfo(
        access_token="auth-manager-token",  # noqa: S106
        persistent_token_id="id-1",  # noqa: S106
    ),
)
@patch("obi_auth.client._get_auth_method")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token_auth_manager(mock_cache, mock_method, mock_auth_manager):
    mock_cache.get.return_value = None
    keycloak_token = KeycloakTokenInfo(access_token="keycloak-token")  # noqa: S106
    mock_method.return_value = lambda *args, **kwargs: keycloak_token

    assert test_module.get_token(token_provider=TokenProvider.auth_manager) == "auth-manager-token"
    mock_auth_manager.assert_called_once()
    assert mock_auth_manager.call_args.args[0] == keycloak_token


@patch("obi_auth.client.auth_manager_exchange_token")
@patch("obi_auth.client._get_auth_method")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token_auth_manager_raises(mock_cache, mock_method, mock_auth_manager):
    mock_cache.get.return_value = None
    mock_method.return_value = lambda *args, **kwargs: KeycloakTokenInfo(
        access_token="keycloak-token"  # noqa: S106
    )
    mock_auth_manager.side_effect = exception.AuthFlowError()

    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module.get_token(token_provider=TokenProvider.auth_manager)


@patch("obi_auth.client.Storage")
@patch("obi_auth.client._get_auth_method")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token_force_refresh(mock_cache, mock_method, mock_storage):
    mock_cache.get.return_value = KeycloakTokenInfo(access_token="cached-token")  # noqa: S106
    fresh_token = KeycloakTokenInfo(access_token="fresh-token")  # noqa: S106
    mock_method.return_value = lambda *args, **kwargs: fresh_token

    result = test_module.get_token(force_refresh=True)

    assert result == "fresh-token"
    mock_cache.get.assert_not_called()
    mock_storage.return_value.clear.assert_called_once_with()
    mock_cache.set.assert_called_once_with(fresh_token, mock_storage.return_value)


def test_get_auth_method():
    res = test_module._get_auth_method(AuthMode.pkce)
    assert res is test_module._pkce_authenticate

    res = test_module._get_auth_method(AuthMode.daf)
    assert res is test_module._daf_authenticate


@patch("obi_auth.flows.pkce.webbrowser")
@patch("obi_auth.client.AuthServer")
def test_pkce_authenticate(mock_server, mock_web, httpx_mock):
    httpx_mock.add_response(method="POST", json={"access_token": "mock-token"})

    mock_local = Mock()
    mock_local.redirect_uri = "mock-redirect-uri"
    mock_local.wait_for_code.return_value = "mock-code"
    mock_server.run.return_value.__enter__.return_value = mock_local

    res = test_module._pkce_authenticate(environment=None)
    assert res == KeycloakTokenInfo(access_token="mock-token")  # noqa: S106

    mock_server.side_effect = exception.AuthFlowError()
    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module._pkce_authenticate(environment=None)

    mock_server.side_effect = exception.ConfigError()
    with pytest.raises(
        exception.ClientError, match="There is a mistake with configuration settings."
    ):
        test_module._pkce_authenticate(environment=None)

    mock_server.side_effect = exception.LocalServerError()
    with pytest.raises(exception.ClientError, match="Local server failed to authenticate."):
        test_module._pkce_authenticate(environment=None)


@patch("obi_auth.client.daf_authenticate")
def test_daf_authenticate(auth_method, httpx_mock):
    auth_method.side_effect = exception.AuthFlowError()
    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module._daf_authenticate(environment=None)


def test_get_token_info():
    payload = {"foo": "bar", "bar": "foo"}

    encoded = jwt.encode(payload, key=None, algorithm="none")

    decoded = test_module.get_token_info(encoded)
    assert decoded == payload


def test_get_user_info(httpx_mock, settings):
    mock_json_response = {"foo": "bar", "bar": "foo"}

    httpx_mock.add_response(
        method="POST",
        url=settings.get_keycloak_user_info_endpoint(override_env="staging"),
        json=mock_json_response,
    )

    res = test_module.get_user_info(token=None, environment="staging")
    assert res == mock_json_response
