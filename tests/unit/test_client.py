from unittest.mock import Mock, patch

import pytest

from obi_auth import client as test_module
from obi_auth import exception


@patch("obi_auth.flow.webbrowser")
@patch("obi_auth.client.AuthServer")
@patch("obi_auth.client._TOKEN_CACHE")
def test_get_token(mock_cache, mock_server, mock_web, httpx_mock):
    mock_cache.get.return_value = "foo"
    assert test_module.get_token() == "foo"

    mock_cache.get.return_value = None

    httpx_mock.add_response(method="POST", json={"access_token": "mock-token"})

    mock_local = Mock()
    mock_local.redirect_uri = "mock-redirect-uri"
    mock_local.wait_for_code.return_value = "mock-code"
    mock_server.run.return_value.__enter__.return_value = mock_local

    res = test_module.get_token()
    assert res == "mock-token"

    mock_server.side_effect = exception.AuthFlowError()
    with pytest.raises(exception.ClientError, match="Authentication process failed."):
        test_module.get_token()

    mock_server.side_effect = exception.ConfigError()
    with pytest.raises(
        exception.ClientError, match="There is a mistake with configuration settings."
    ):
        test_module.get_token()

    mock_server.side_effect = exception.LocalServerError()
    with pytest.raises(exception.ClientError, match="Local server failed to authenticate."):
        test_module.get_token()
