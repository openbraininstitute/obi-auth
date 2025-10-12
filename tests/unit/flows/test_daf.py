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


@patch("obi_auth.flows.daf._poll_device_code_token")
@patch("obi_auth.flows.daf._display_auth_prompt")
@patch("obi_auth.flows.daf._get_device_url_code")
@patch("builtins.print")
def test_daf_authenticate_success(
    mock_print, mock_get_device_url, mock_display_prompt, mock_poll, device_info
):
    """Test daf_authenticate returns token on successful authentication."""
    mock_get_device_url.return_value = device_info
    mock_poll.return_value = "test_token"

    result = test_module.daf_authenticate(environment=DeploymentEnvironment.staging)

    assert result == "test_token"
    mock_display_prompt.assert_called_once_with(device_info)
    mock_poll.assert_called_once_with(device_info, DeploymentEnvironment.staging)
    mock_print.assert_called_with("\r   ✓ Authentication completed successfully!", flush=True)


@patch("obi_auth.flows.daf._poll_device_code_token")
@patch("obi_auth.flows.daf._display_auth_prompt")
@patch("obi_auth.flows.daf._get_device_url_code")
@patch("builtins.print")
def test_daf_authenticate_failure(
    mock_print, mock_get_device_url, mock_display_prompt, mock_poll, device_info
):
    """Test daf_authenticate raises error on authentication failure."""
    mock_get_device_url.return_value = device_info
    mock_poll.return_value = None

    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module.daf_authenticate(environment=DeploymentEnvironment.staging)

    mock_display_prompt.assert_called_once_with(device_info)
    mock_poll.assert_called_once_with(device_info, DeploymentEnvironment.staging)
    mock_print.assert_called_with("\r   ✗ Authentication failed - timeout reached", flush=True)


def test_device_code_token(httpx_mock, device_info):
    httpx_mock.add_response(method="POST", json={"access_token": "foo"})

    res = test_module._get_device_code_token(device_info, None)
    assert res == "foo"

    httpx_mock.add_response(method="POST", status_code=400, json={"error": "authorization_pending"})
    res = test_module._get_device_code_token(device_info, None)
    assert res is None


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token(mock_code_token_method, device_info):
    """Test _poll_device_code_token returns None when no token is available."""
    mock_code_token_method.return_value = None

    device_info.expires_in = 1
    result = test_module._poll_device_code_token(device_info, None)
    assert result is None


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token_success(mock_code_token_method, device_info):
    """Test _poll_device_code_token returns token on success."""
    mock_code_token_method.return_value = "test_token"

    result = test_module._poll_device_code_token(device_info, DeploymentEnvironment.staging)

    assert result == "test_token"
    mock_code_token_method.assert_called_once_with(device_info, DeploymentEnvironment.staging)


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token_timeout(mock_code_token_method, device_info):
    """Test _poll_device_code_token returns None on timeout."""
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

    result = test_module._poll_device_code_token(timeout_device_info, DeploymentEnvironment.staging)
    assert result is None


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


@patch("obi_auth.flows.daf.httpx.post")
def test_get_device_url_code(mock_post, device_info):
    """Test _get_device_url_code function."""
    mock_response = mock_post.return_value
    mock_response.json.return_value = device_info.model_dump(mode="json")

    result = test_module._get_device_url_code(environment=DeploymentEnvironment.staging)

    assert result == device_info
    mock_post.assert_called_once()


@patch("builtins.print")
def test_display_terminal_auth_prompt(mock_print, device_info):
    """Test _display_terminal_auth_prompt function."""
    test_module._display_terminal_auth_prompt(device_info)

    # Verify print was called for each part of the message
    # title + 3 steps + url + verification_uri_complete = 6 calls
    assert mock_print.call_count == 6
