from unittest.mock import patch

import pytest

from obi_auth import browser as test_module
from obi_auth.exception import ObiAuthError


@patch("obi_auth.browser.webbrowser")
@patch("obi_auth.browser._close_tab")
def test_open_in_browser(mock_tab, mock_webbrowser):
    url = "foo"
    with test_module.open_in_browser(url=url):
        mock_webbrowser.open_new_tab.assert_called_once_with(url)
    mock_tab.assert_called_once()


@patch("obi_auth.browser.platform")
@patch("obi_auth.browser.pyautogui")
def test_close_tab(mock_gui, mock_platform):
    mock_platform.system.return_value = "Windows"
    test_module._close_tab()
    mock_gui.hotkey.assert_called_with("ctrl", "w", interval=test_module.KEY_INTERVAL)

    mock_platform.system.return_value = "Linux"
    test_module._close_tab()
    mock_gui.hotkey.assert_called_with("ctrl", "w", interval=test_module.KEY_INTERVAL)

    mock_platform.system.return_value = "Darwin"
    test_module._close_tab()
    mock_gui.hotkey.assert_called_with("command", "w", interval=test_module.KEY_INTERVAL)

    mock_platform.system.return_value = "Foo"
    with pytest.raises(ObiAuthError, match="Unsupported platform Foo"):
        test_module._close_tab()
