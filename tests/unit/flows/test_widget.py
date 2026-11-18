from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
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
    access_token = jwt.encode(
        {"name": "Jane Doe", "preferred_username": "jdoe"}, "x" * 32, algorithm="HS256"
    )
    fake_widget = MagicMock()
    fake_widget.access_token = access_token
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    # Simulate run_ui_poll_loop by invoking the supplied callback once.
    def fake_poll_loop(f, sleep, n):
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
    fake_widget.auth_state = "in_progress"
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    # deadline = monotonic() + timeout (=0). First in-loop check is before the
    # deadline (returns None -> still waiting), second is past it (-> timeout).
    mock_time.monotonic.side_effect = [0, -1, 10_000]

    def fake_poll_loop(f, sleep, n):
        # Drive the callback until it returns a non-None value, as the real loop does.
        while True:
            x = f()
            if x is not None:
                return x

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(AuthCancelledError, match="was not completed within"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    # The widget must be cleared even when the flow times out.
    mock_clear.assert_called_once_with(handle)


def _run_flow(widget, times, on_check=None):
    """Run the flow with a fake poll loop; ``times`` are successive ``time.monotonic()`` values."""
    clock = iter(times)

    def fake_poll_loop(f, sleep, n):
        i = 0
        while True:
            if on_check:
                on_check(i, widget)
            x = f()
            if x is not None:
                return x
            i += 1

    with (
        patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True),
        patch("obi_auth.flows.widget.get_widget", return_value=widget),
        patch("obi_auth.flows.widget._display", return_value=object()),
        patch("obi_auth.flows.widget._clear") as mock_clear,
        patch("obi_auth.flows.widget.time.monotonic", side_effect=lambda: next(clock)),
        patch.dict("sys.modules", {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)}),
    ):
        return test_module.widget_authenticate(
            environment=DeploymentEnvironment.staging
        ), mock_clear


def _widget(**traits):
    return SimpleNamespace(**{"access_token": "", "auth_error": "", **traits})


def test_widget_authenticate_stops_when_sign_in_is_never_started(monkeypatch):
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_START_TIMEOUT_SECONDS", 20)
    with pytest.raises(AuthCancelledError, match="was not started"):
        _run_flow(_widget(auth_state="idle"), times=[0, 5, 19.9, 20])


def test_widget_authenticate_waits_while_sign_in_is_in_progress(monkeypatch):
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_START_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_TIMEOUT_SECONDS", 120)

    def frontend(i, widget):
        if i == 1:
            widget.auth_state = "in_progress"
        if i == 3:
            widget.access_token = "the-token"  # noqa: S105

    result, _ = _run_flow(_widget(auth_state="idle"), times=[0, 5, 10, 50, 100], on_check=frontend)
    assert result.access_token == "the-token"  # noqa: S105


def test_widget_authenticate_stops_at_once_when_popup_is_closed():
    def frontend(i, widget):
        if i == 1:
            widget.auth_state = "cancelled"
            widget.auth_error = "cancelled"

    with pytest.raises(AuthCancelledError, match="Sign-in was cancelled"):
        _run_flow(_widget(auth_state="in_progress"), times=[0, 1, 2], on_check=frontend)


def test_widget_authenticate_times_out_when_sign_in_never_finishes(monkeypatch):
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_START_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_TIMEOUT_SECONDS", 120)
    with pytest.raises(AuthCancelledError, match="was not completed within 120 s"):
        _run_flow(_widget(auth_state="in_progress"), times=[0, 1, 50, 120, 121])


@pytest.mark.parametrize(
    ("auth_error", "message"),
    [("cancelled", "Sign-in was cancelled"), ("error", "Sign-in failed, see the message")],
)
@patch("obi_auth.flows.widget._clear")
@patch("obi_auth.flows.widget._display")
@patch("obi_auth.flows.widget.get_widget")
@patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True)
def test_widget_authenticate_aborts_on_widget_error(
    mock_in_nb, mock_get_widget, mock_display, mock_clear, auth_error, message
):
    # The widget signals a terminal outcome (popup closed / sign-in error) via
    # its auth_error trait; the flow must stop immediately, not hang to timeout.
    fake_widget = MagicMock()
    fake_widget.access_token = ""
    fake_widget.auth_error = auth_error
    mock_get_widget.return_value = fake_widget
    handle = object()
    mock_display.return_value = handle

    def fake_poll_loop(f, sleep, n):
        while True:
            x = f()
            if x is not None:
                return x

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(AuthCancelledError, match=f"{message}.*Re-run the cell"):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    if auth_error == "cancelled":
        mock_clear.assert_called_once_with(handle)
        fake_widget.disable.assert_not_called()
    else:
        mock_clear.assert_not_called()
        fake_widget.disable.assert_called_once_with()


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

    def fake_poll_loop(f, sleep, n):
        raise KeyboardInterrupt

    with patch.dict(
        "sys.modules",
        {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)},
    ):
        with pytest.raises(KeyboardInterrupt):
            test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    mock_clear.assert_called_once_with(handle)


def _jwt(claims):
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


def test_widget_authenticate_handles_many_messages_per_poll_iteration():
    seen = {}

    def fake_poll_loop(f, sleep, n):
        seen["n"] = n
        return f()

    widget = _widget(auth_state="idle", access_token="the-token")  # noqa: S106
    with (
        patch("obi_auth.flows.widget.is_running_in_notebook", return_value=True),
        patch("obi_auth.flows.widget.get_widget", return_value=widget),
        patch("obi_auth.flows.widget._display", return_value=object()),
        patch("obi_auth.flows.widget._clear"),
        patch.dict("sys.modules", {"jupyter_ui_poll": MagicMock(run_ui_poll_loop=fake_poll_loop)}),
    ):
        test_module.widget_authenticate(environment=DeploymentEnvironment.staging)

    assert seen["n"] > 1


def test_sign_in_watcher_counts_the_sign_in_timeout_from_when_the_popup_opens(monkeypatch):
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_START_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(test_module.settings, "NOTEBOOK_TIMEOUT_SECONDS", 120)
    clock = iter([0, 5, 10, 129, 130])
    widget = _widget(auth_state="idle")
    with patch("obi_auth.flows.widget.time.monotonic", side_effect=lambda: next(clock)):
        watcher = test_module._SignInWatcher(widget)
        assert watcher.check() is None
        widget.auth_state = "in_progress"
        assert watcher.check() is None
        assert watcher.check() is None
        assert watcher.check() is test_module._Outcome.TIMEOUT
