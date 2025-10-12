from unittest.mock import patch

import pytest

from obi_auth.exception import AuthFlowError
from obi_auth.flows import daf as test_module
from obi_auth.typedef import AuthDeviceInfo, DeploymentEnvironment


@pytest.fixture
def device_info():
    return AuthDeviceInfo.model_validate(
        {
            "user_code": "user_code",
            "verification_uri": "foo",
            "verification_uri_complete": "foo",
            "expires_in": 2,
            "interval": 1,
            "device_code": "bar",
        }
    )


def test_daf_authenticate(httpx_mock, device_info):
    httpx_mock.add_response(method="POST", json=device_info.model_dump(mode="json"))
    httpx_mock.add_response(
        method="POST",
        json={
            "access_token": "token",
        },
    )
    res = test_module.daf_authenticate(environment=DeploymentEnvironment.staging)
    assert res == "token"


def test_device_code_token(httpx_mock, device_info):
    httpx_mock.add_response(method="POST", json={"access_token": "foo"})

    res = test_module._get_device_code_token(device_info, None)
    assert res == "foo"

    httpx_mock.add_response(method="POST", status_code=400, json={"error": "authorization_pending"})
    res = test_module._get_device_code_token(device_info, None)
    assert res is None


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token(mock_code_token_method, device_info):
    mock_code_token_method.return_value = None

    device_info.expires_in = 1
    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_device_code_token(device_info, None)


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token_success(mock_code_token_method, device_info):
    """Test _poll_device_code_token returns token on success."""
    mock_code_token_method.return_value = "test_token"

    result = test_module._poll_device_code_token(device_info, DeploymentEnvironment.staging)

    assert result == "test_token"
    mock_code_token_method.assert_called_once_with(device_info, DeploymentEnvironment.staging)


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token_timeout(mock_code_token_method, device_info):
    """Test _poll_device_code_token raises error on timeout."""
    mock_code_token_method.return_value = None

    # Create a new device_info with max_retries=1
    timeout_device_info = AuthDeviceInfo.model_validate(
        {
            "user_code": "user_code",
            "verification_uri": "foo",
            "verification_uri_complete": "foo",
            "device_code": "bar",
            "expires_in": 2,
            "interval": 1,
            "max_retries": 1,
        }
    )

    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_device_code_token(timeout_device_info, DeploymentEnvironment.staging)


@patch("obi_auth.flows.daf.is_running_in_notebook")
@patch("obi_auth.flows.daf._display_notebook_auth_prompt")
@patch("obi_auth.flows.daf._display_terminal_auth_prompt")
def test_display_auth_prompt_notebook(mock_terminal, mock_notebook, mock_is_notebook, device_info):
    """Test _display_auth_prompt calls notebook prompt when in notebook."""
    mock_is_notebook.return_value = True

    test_module._display_auth_prompt(device_info)

    mock_notebook.assert_called_once_with(device_info)
    mock_terminal.assert_not_called()


@patch("obi_auth.flows.daf.is_running_in_notebook")
@patch("obi_auth.flows.daf._display_notebook_auth_prompt")
@patch("obi_auth.flows.daf._display_terminal_auth_prompt")
def test_display_auth_prompt_terminal(mock_terminal, mock_notebook, mock_is_notebook, device_info):
    """Test _display_auth_prompt calls terminal prompt when not in notebook."""
    mock_is_notebook.return_value = False

    test_module._display_auth_prompt(device_info)

    mock_terminal.assert_called_once_with(device_info)
    mock_notebook.assert_not_called()


@patch("rich.console.Console")
def test_display_notebook_auth_prompt_success(mock_console, device_info):
    """Test _display_notebook_auth_prompt works with Rich."""
    mock_console_instance = mock_console.return_value

    test_module._display_notebook_auth_prompt(device_info)

    mock_console_instance.print.assert_called_once()


@patch("rich.console.Console", side_effect=ImportError)
@patch("obi_auth.flows.daf._display_terminal_auth_prompt")
def test_display_notebook_auth_prompt_fallback(mock_terminal, mock_console, device_info):
    """Test _display_notebook_auth_prompt falls back to terminal on Rich error."""
    test_module._display_notebook_auth_prompt(device_info)

    mock_terminal.assert_called_once_with(device_info)


@patch("obi_auth.flows.daf._get_device_code_token")
@patch("builtins.print")
def test_poll_with_terminal_progress_success(mock_print, mock_get_token, device_info):
    """Test _poll_with_terminal_progress returns token on success."""
    mock_get_token.return_value = "test_token"

    result = test_module._poll_with_terminal_progress(device_info, DeploymentEnvironment.staging, 5)

    assert result == "test_token"
    mock_get_token.assert_called_once_with(device_info, DeploymentEnvironment.staging)


@patch("obi_auth.flows.daf._get_device_code_token")
@patch("builtins.print")
def test_poll_with_terminal_progress_timeout(mock_print, mock_get_token, device_info):
    """Test _poll_with_terminal_progress raises error on timeout."""
    mock_get_token.return_value = None

    # Create a new device_info with max_retries=1
    timeout_device_info = AuthDeviceInfo.model_validate(
        {
            "user_code": "user_code",
            "verification_uri": "foo",
            "verification_uri_complete": "foo",
            "device_code": "bar",
            "expires_in": 2,
            "interval": 1,
            "max_retries": 1,
        }
    )

    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_with_terminal_progress(
            timeout_device_info, DeploymentEnvironment.staging, 1
        )
