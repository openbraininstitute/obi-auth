from pathlib import Path
from unittest.mock import Mock, patch

from obi_auth import util as test_module


@patch("obi_auth.util.platform")
@patch("pathlib.Path.home")
@patch("obi_auth.util.get_machine_salt")
def test_get_config_path(mock_salt, mock_home, mock_platform, tmp_path):
    mock_home.return_value = Path(tmp_path)
    mock_salt.return_value = Mock(hex=Mock(return_value="foo"))

    mock_platform.system.return_value = "Windows"
    res = test_module.get_config_path()
    assert res == Path(f"{tmp_path}/AppData/Roaming/obi-auth/foo.json")
    assert res.parent.exists()

    mock_platform.system.return_value = "Linux"
    res = test_module.get_config_path()
    assert res == Path(f"{tmp_path}/.config/obi-auth/foo.json")
    assert res.parent.exists()
