import sys
from unittest.mock import Mock

# mock pyautogui module because it checks for an existing X-server at import time
# which breaks github actions
sys.modules["pyautogui"] = Mock()
