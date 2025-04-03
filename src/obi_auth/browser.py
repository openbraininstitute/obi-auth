"""Browser handling module."""

import platform
import webbrowser
from contextlib import contextmanager

import pyautogui

from obi_auth.exception import ObiAuthError

KEY_INTERVAL = 0.1


@contextmanager
def open_in_browser(url: str):
    """Open url in a new browser tab and close it afterwards."""
    webbrowser.open_new_tab(url)
    yield
    _close_tab()


def _close_tab():
    """Close tab by pressing the respective hotkey in each platform."""
    match platform.system():
        case "Windows" | "Linux":
            pyautogui.hotkey("ctrl", "w", interval=KEY_INTERVAL)
        case "Darwin":
            pyautogui.hotkey("command", "w", interval=KEY_INTERVAL)
        case _:
            raise ObiAuthError(f"Unsupported platform {platform.system()}")
