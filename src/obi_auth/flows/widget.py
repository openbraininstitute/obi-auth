"""Interactive notebook widget authentication flow (auth_mode="notebook").

This flow renders an ``ipyauth-pkce`` sign-in widget in the notebook cell and
blocks until the user signs in, then returns the resulting Keycloak access
token. This lets notebooks keep the synchronous
``token = get_token(..., auth_mode="notebook")`` contract and only change the
``auth_mode`` argument.

Blocking a cell while still processing the widget's frontend comm messages
(and *not* prematurely running the cells below, so ``Run All`` keeps working)
is handled by ``jupyter-ui-poll``.
"""

import enum
import time

from obi_auth.config import settings
from obi_auth.exception import AuthCancelledError, AuthFlowError
from obi_auth.typedef import DeploymentEnvironment, KeycloakTokenInfo
from obi_auth.util import decode_token, is_running_in_notebook
from obi_auth.widget import get_widget

_MISSING_POLL_MSG = (
    "The notebook widget auth mode requires the optional 'jupyter-ui-poll' "
    "dependency. Install it with: pip install obi-auth[notebook]"
)

_POLL_SLEEP_SECONDS = 0.1
_POLL_MESSAGES_PER_ITERATION = 50


def widget_authenticate(*, environment: DeploymentEnvironment) -> KeycloakTokenInfo:
    """Authenticate interactively via the notebook sign-in widget.

    Renders the widget, blocks until the user signs in (or a timeout is
    reached), and returns the resulting Keycloak access token.

    Raises:
        AuthFlowError: If not running in a notebook, the ``notebook`` extra is
            missing, or the sign-in times out before a token is received.
    """
    if not is_running_in_notebook():
        raise AuthFlowError(
            "auth_mode='notebook' is only supported inside a Jupyter notebook. "
            "Use auth_mode='pkce' or auth_mode='daf' from a terminal or script."
        )

    try:
        from jupyter_ui_poll import run_ui_poll_loop  # ty: ignore[import-not-found]
    except ImportError as exc:
        raise AuthFlowError(_MISSING_POLL_MSG) from exc

    widget = get_widget(environment=environment)
    handle = _display(widget)

    watcher = _SignInWatcher(widget)

    try:
        outcome: _Outcome = run_ui_poll_loop(
            watcher.check, sleep=_POLL_SLEEP_SECONDS, n=_POLL_MESSAGES_PER_ITERATION
        )
    except BaseException:
        _clear(handle)
        raise

    match outcome:
        case _Outcome.NOT_STARTED:
            _clear(handle)
            raise AuthCancelledError(
                "Sign-in was not started. Re-run the cell and click 'Sign In' to continue."
            )
        case _Outcome.ABORTED:
            _clear(handle)
            if widget.auth_error == "cancelled":
                raise AuthCancelledError("Sign-in was cancelled. Re-run the cell to try again.")
            raise AuthCancelledError("Sign-in failed. Re-run the cell to try again.")
        case _Outcome.TIMEOUT:
            _clear(handle)
            raise AuthCancelledError(
                f"Sign-in was not completed within {settings.NOTEBOOK_TIMEOUT_SECONDS} s. "
                "Re-run the cell to try again."
            )

    token = widget.access_token
    # Replace the interactive widget with a short confirmation so the sign-in
    # does not simply vanish, while keeping a consistent, non-interactive end
    # state whether or not a sign-in was actually needed.
    _clear(handle, f"\u2713 Signed in{_signed_in_suffix(token)}")

    return KeycloakTokenInfo(access_token=token)


def _signed_in_suffix(token: str) -> str:
    """Build " as <name> (<preferred_username>)" from the token claims.

    Degrades to whichever claim is present (or an empty suffix if neither is).
    """
    try:
        claims = decode_token(token)
    except Exception:  # noqa: BLE001 - never fail the flow over a cosmetic label
        return ""
    name = claims.get("name")
    username = claims.get("preferred_username")
    if name and username:
        return f" as {name} ({username})"
    if name or username:
        return f" as {name or username}"
    return ""


class _Outcome(enum.Enum):
    SIGNED_IN = enum.auto()
    NOT_STARTED = enum.auto()
    ABORTED = enum.auto()
    TIMEOUT = enum.auto()


class _SignInWatcher:
    def __init__(self, widget) -> None:
        self._widget = widget
        self._start_deadline = time.monotonic() + settings.NOTEBOOK_START_TIMEOUT_SECONDS
        self._sign_in_deadline: float | None = None

    def check(self) -> _Outcome | None:
        widget = self._widget
        if widget.access_token:
            return _Outcome.SIGNED_IN
        if widget.auth_error:
            return _Outcome.ABORTED
        now = time.monotonic()
        if self._sign_in_deadline is None and widget.auth_state == "in_progress":
            self._sign_in_deadline = now + settings.NOTEBOOK_TIMEOUT_SECONDS
        if self._sign_in_deadline is None:
            return _Outcome.NOT_STARTED if now >= self._start_deadline else None
        return _Outcome.TIMEOUT if now >= self._sign_in_deadline else None


def _display(widget):
    """Display the widget in the current notebook cell, returning its handle."""
    from IPython.display import display  # ty: ignore[import-not-found]

    return display(widget, display_id=True)


def _clear(handle, message: str = "") -> None:
    """Replace the displayed widget with a short message (or empty output)."""
    if handle is None:
        return
    from IPython.display import HTML  # ty: ignore[import-not-found]

    if message:
        html = f'<div style="color:#002766;font-size:13px;padding:3px">{message}</div>'
    else:
        html = ""
    handle.update(HTML(html))
