from pathlib import Path
from unittest.mock import patch

from obi_auth import util as test_module


def test_machine_salt():
    res1 = test_module.get_machine_salt()
    res2 = test_module.get_machine_salt()
    assert res1 == res2


@patch("pathlib.Path.home")
def test_get_config_dir(mock_home):
    mock_home.return_value = Path("/foo")
    res = test_module.get_config_dir()
    assert res == Path("/foo/.config/obi-auth")
