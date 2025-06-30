from unittest.mock import Mock, patch

import jwt
import pytest

from obi_auth import client as test_module
from obi_auth import exception
from obi_auth.typedef import AuthMode


@patch("obi_auth.client._get_auth_method")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token(mock_cache, mock_method):
    mock_cache.get.return_value = "foo"
    assert test_module.get_token() == "foo"

    mock_cache.get.return_value = None

    mock_method.return_value = lambda x: "mock-token"

    assert test_module.get_token() == "mock-token"


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

    res = test_module._pkce_authenticate(None)
    assert res == "mock-token"

    mock_server.side_effect = exception.AuthFlowError()
    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module._pkce_authenticate(None)

    mock_server.side_effect = exception.ConfigError()
    with pytest.raises(
        exception.ClientError, match="There is a mistake with configuration settings."
    ):
        test_module._pkce_authenticate(None)

    mock_server.side_effect = exception.LocalServerError()
    with pytest.raises(exception.ClientError, match="Local server failed to authenticate."):
        test_module._pkce_authenticate(None)


@patch("obi_auth.client.daf_authenticate")
def test_daf_authenticate(auth_method, httpx_mock):
    auth_method.side_effect = exception.AuthFlowError()
    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module._daf_authenticate(None)


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
