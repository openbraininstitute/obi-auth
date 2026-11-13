from unittest.mock import MagicMock, patch

import pytest

from obi_auth.exception import AuthCancelledError, AuthFlowError
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


@patch("obi_auth.flows.widget._clear")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_success(mock_in_nb, mock_get_widget, mock_display, mock_clear):
    import jwt

    access_token = jwt.encode(
        {"name": "Jane Doe", "preferred_username": "jdoe"}, "x" * 32, algorithm="HS256"
    )
    fake_widget = MagicMock()
    fake_widget.access_token = access_token
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    # Simulate run_ui_poll_loop by invoking the supplied callback once.
    def fake_poll_loop(f, sleep):
        return f()

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        result = test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    assert isinstance(result, KeycloakTokenInfo)
    assert result.access_token == access_token
    mock_get_widget.assert_called_once_with(environment=DeploymentEnvironment.staging)
    mock_display.assert_called_once_with(fake_widget)
    # On success the widget is replaced with a confirmation built from token claims.
    mock_clear.assert_called_once()
    clear_args, _ = mock_clear.call_args
    assert clear_args[0] is handle
    assert clear_args[1] == "\u2713 Signed in as Jane Doe (jdoe)"


@patch("obi_auth.flows.widget._clear")
@patch("obi_auth.flows.widget.time")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_timeout(
    mock_in_nb, mock_get_widget, mock_display, mock_time, mock_clear
):
    fake_widget = MagicMock()
    fake_widget.access_token = ""  # never signs in
    fake_widget.auth_error = ""  # no terminal error -> must reach the deadline
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

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
        with pytest.raises(AuthCancelledError, match="Re-run the cell"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    # The widget must be cleared even when the flow times out.
    mock_clear.assert_called_once_with(handle)


@pytest.mark.parametrize("auth_error", ["cancelled", "error"])
@patch("obi_auth.flows.widget._clear")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_aborts_on_widget_error(
    mock_in_nb, mock_get_widget, mock_display, mock_clear, auth_error
):
    # The widget signals a terminal outcome (popup closed / sign-in error) via
    # its auth_error trait; the flow must stop immediately, not hang to timeout.
    fake_widget = MagicMock()
    fake_widget.access_token = ""
    fake_widget.auth_error = auth_error
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    def fake_poll_loop(f, sleep):
        while True:
            x = f()
            if x is not None:
                return x

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(AuthCancelledError, match="Re-run the cell"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    mock_clear.assert_called_once_with(handle)


@patch("obi_auth.flows.widget._clear")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_clears_when_poll_raises(
    mock_in_nb, mock_get_widget, mock_display, mock_clear
):
    # If the poll loop itself raises (e.g. KeyboardInterrupt), the widget must
    # still be cleared and the original exception must propagate.
    fake_widget = MagicMock()
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    def fake_poll_loop(f, sleep):
        raise KeyboardInterrupt

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(KeyboardInterrupt):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    mock_clear.assert_called_once_with(handle)


def _jwt(claims):
    import jwt

    return jwt.encode(claims, "x" * 32, algorithm="HS256")


def test_signed_in_suffix_with_name_and_username():
    suffix = test_module._signed_in_suffix(_jwt({"name": "Jane Doe", "preferred_username": "jdoe"}))
    assert suffix == " as Jane Doe (jdoe)"


def test_signed_in_suffix_with_only_one_claim():
    assert test_module._signed_in_suffix(_jwt({"name": "Jane Doe"})) == " as Jane Doe"
    assert test_module._signed_in_suffix(_jwt({"preferred_username": "jdoe"})) == " as jdoe"


def test_signed_in_suffix_with_no_claims():
    assert test_module._signed_in_suffix(_jwt({"sub": "123"})) == ""


def test_auth_cancelled_renders_as_single_line():
    exc = AuthCancelledError("Sign-in was not completed. Re-run the cell to try again.")
    # IPython calls _render_traceback_ to show a concise message (no stack).
    assert exc._render_traceback_() == ["Sign-in was not completed. Re-run the cell to try again."]


def test_signed_in_suffix_with_undecodable_token():
    # Never raises on a non-JWT value; returns an empty suffix.
    assert test_module._signed_in_suffix("not-a-jwt") == ""


def test_display_invokes_ipython_display():
    fake_widget = object()
    handle = object()
    fake_display = MagicMock(return_value=handle)
    with patch.dict(
        "sys.modules",
        {"IPython.display": MagicMock(display=fake_display)},
    ):
        result = test_module._display(fake_widget)
    fake_display.assert_called_once_with(fake_widget, display_id=True)
    assert result is handle


def test_clear_updates_handle_with_empty_output():
    handle = MagicMock()
    fake_html = MagicMock(return_value="empty")
    with patch.dict(
        "sys.modules",
        {"IPython.display": MagicMock(HTML=fake_html)},
    ):
        test_module._clear(handle)
    fake_html.assert_called_once_with("")
    handle.update.assert_called_once_with("empty")


def test_clear_updates_handle_with_message():
    handle = MagicMock()
    fake_html = MagicMock(return_value="rendered")
    with patch.dict(
        "sys.modules",
        {"IPython.display": MagicMock(HTML=fake_html)},
    ):
        test_module._clear(handle, "\u2713 Signed in as Jane \u2014 token ready")
    # The message is embedded in the HTML passed to HTML(...).
    (html_arg,), _ = fake_html.call_args
    assert "Signed in as Jane" in html_arg
    handle.update.assert_called_once_with("rendered")


def test_clear_is_noop_when_handle_is_none():
    # Must not raise when there is no display handle (e.g. display_id unsupported).
    test_module._clear(None)
    test_module._clear(None, "message")
