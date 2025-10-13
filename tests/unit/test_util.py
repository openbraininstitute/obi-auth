from pathlib import Path
from unittest.mock import patch

from obi_auth import util as test_module


def test_machine_salt():
    res1 = test_module.get_machine_salt()
    res2 = test_module.get_machine_salt()
    assert res1 == res2


@patch("sys.modules")
def test_is_running_in_notebook_false(mock_modules):
    """Test notebook detection returns False when not in notebook."""
    mock_modules.__contains__.return_value = False
    assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipython(mock_modules):
    """Test notebook detection returns True when IPython is available."""
    mock_modules.__contains__.return_value = True

    with patch("obi_auth.util.get_ipython") as mock_get_ipython:
        mock_ipython = mock_get_ipython.return_value
        mock_ipython.__class__.__name__ = "ZMQInteractiveShell"

        assert test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_jupyter_modules(mock_modules):
    """Test notebook detection returns True when jupyter modules are present."""
    mock_modules.__contains__.side_effect = lambda x: x in ["jupyter", "notebook"]

    assert test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipykernel(mock_modules):
    """Test notebook detection returns True when ipykernel is present."""
    mock_modules.__contains__.side_effect = lambda x: x == "ipykernel"

    assert test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipython_none(mock_modules):
    """Test notebook detection returns False when IPython returns None."""
    # Mock IPython in modules but return False for other checks
    mock_modules.__contains__.side_effect = lambda x: x == "IPython"

    with patch("obi_auth.util.get_ipython") as mock_get_ipython:
        mock_get_ipython.return_value = None

        assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipython_wrong_class(mock_modules):
    """Test notebook detection returns False when IPython is not ZMQInteractiveShell."""
    mock_modules.__contains__.return_value = True

    with patch("obi_auth.util.get_ipython") as mock_get_ipython:
        mock_ipython = mock_get_ipython.return_value
        mock_ipython.__class__.__name__ = "TerminalInteractiveShell"

        assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_attribute_error(mock_modules):
    """Test notebook detection handles AttributeError gracefully."""
    mock_modules.__contains__.return_value = True

    with patch("obi_auth.util.get_ipython") as mock_get_ipython:
        # Make get_ipython raise AttributeError when accessing __class__
        mock_ipython = mock_get_ipython.return_value
        mock_ipython.__class__ = property(lambda self: (_ for _ in ()).throw(AttributeError))

        assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_import_error_during_check(mock_modules):
    """Test notebook detection handles ImportError during module check."""
    # Mock IPython in modules but return False for other checks
    mock_modules.__contains__.side_effect = lambda x: x == "IPython"

    with patch("obi_auth.util.get_ipython") as mock_get_ipython:
        mock_get_ipython.return_value = None

        # Mock the any() call to raise ImportError
        with patch("builtins.any", side_effect=ImportError):
            assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipython_import_error(mock_modules):
    """Test notebook detection handles ImportError during IPython import."""
    mock_modules.__contains__.side_effect = lambda x: x == "IPython"

    with patch("IPython.get_ipython", side_effect=ImportError):
        assert not test_module.is_running_in_notebook()


@patch("sys.modules")
def test_is_running_in_notebook_ipython_attribute_error(mock_modules):
    """Test notebook detection handles AttributeError during IPython check."""
    mock_modules.__contains__.side_effect = lambda x: x == "IPython"

    with patch("IPython.get_ipython") as mock_get_ipython:
        mock_ipython = mock_get_ipython.return_value
        mock_ipython.__class__ = property(lambda self: (_ for _ in ()).throw(AttributeError))

        assert not test_module.is_running_in_notebook()


@patch("pathlib.Path.home")
def test_get_config_dir(mock_home):
    mock_home.return_value = Path("/foo")
    res = test_module.get_config_dir()
    assert res == Path("/foo/.config/obi-auth")
