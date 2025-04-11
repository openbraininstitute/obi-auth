import os
import stat
from pathlib import Path
from unittest.mock import Mock, patch

from obi_auth import util as test_module


@patch("pathlib.Path.home")
@patch("obi_auth.util.get_machine_salt")
def test_get_config_path(mock_salt, mock_home, tmp_path):
    directory = Path(tmp_path)
    mock_home.return_value = directory
    mock_salt.return_value = Mock(hex=Mock(return_value="foo"))

    expected_dir = Path(f"{tmp_path}/.config/obi-auth")

    res = test_module.get_config_path()
    assert res == expected_dir / "foo.json"
    assert res.parent.exists()

    # check that directory create with correct permissions
    assert stat.S_IMODE(os.lstat(expected_dir).st_mode) == 0o700

    # check that the permissions for an existing dir will change
    expected_dir.chmod(0o777)
    assert stat.S_IMODE(os.lstat(expected_dir).st_mode) == 0o777
    test_module.get_config_path()
    assert stat.S_IMODE(os.lstat(expected_dir).st_mode) == 0o700
