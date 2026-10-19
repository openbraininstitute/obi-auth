from unittest.mock import MagicMock, patch

import pytest

from obi_auth.exception import AuthFlowError
from obi_auth.flows import widget as test_module
from obi_auth.typedef import DeploymentEnvironment, KeycloakTokenInfo


@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=False)
def test_widget_authenticate_outside_notebook(mock_in_nb):
    with pytest.raises(AuthFlowError, match="only supported inside a Jupyter notebook"):
        test_module.widget_authenticate(environment=DeploymentEnvironment.staging)


@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_missing_poll_dependency(mock_in_nb):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jupyter_ui_poll":
            raise ImportError("no jupyter_ui_poll")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(AuthFlowError, match=r"pip install obi-auth\[notebook\]"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)


@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_success(mock_in_nb, mock_get_widget, mock_display):
    fake_widget = MagicMock()
    fake_widget.access_token = "the-token"  # noqa: S105
    mock_get_widget.return_value = fake_widget

    # Simulate run_ui_poll_loop by invoking the supplied callback once.
    def fake_poll_loop(f, sleep):
        return f()

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        result = test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    assert isinstance(result, KeycloakTokenInfo)
    assert result.access_token == "the-token"  # noqa: S105
    mock_get_widget.assert_called_once_with(environment=DeploymentEnvironment.staging)
    mock_display.assert_called_once_with(fake_widget)


@patch("obi_auth.flows.widget.time")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_timeout(mock_in_nb, mock_get_widget, mock_display, mock_time):
    fake_widget = MagicMock()
    fake_widget.access_token = ""  # never signs in
    mock_get_widget.return_value = fake_widget

    # deadline = monotonic() + timeout (=0). First in-loop check is before the
    # deadline (returns None -> still waiting), second is past it (-> timeout).
    mock_time.monotonic.side_effect = [0, -1, 10_000]

    def fake_poll_loop(f, sleep):
        # Drive the callback until it returns a non-None value, as the real loop does.
        while True:
            x = f()
            if x is not None:
                return x

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(AuthFlowError, match="timed out"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)


def test_display_invokes_ipython_display():
    fake_widget = object()
    fake_display = MagicMock()
    with patch.dict(
        "sys.modules",
        {"IPython.display": MagicMock(display=fake_display)},
    ):
        test_module._display(fake_widget)
    fake_display.assert_called_once_with(fake_widget)
