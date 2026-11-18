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

    deadline = time.monotonic() + settings.NOTEBOOK_TIMEOUT_SECONDS

    def _check():
        # None keeps the poll loop running (still servicing comm events); a value stops it.
        if widget.access_token:
            return widget.access_token
        # The widget signals a terminal outcome (popup closed, or a sign-in
        # error) so we stop immediately instead of hanging until the deadline.
        if getattr(widget, "auth_error", ""):
            return _ABORTED
        if time.monotonic() >= deadline:
            return _TIMEOUT
        return None

    try:
        token = run_ui_poll_loop(_check, sleep=_POLL_SLEEP_SECONDS, n=_POLL_MESSAGES_PER_ITERATION)
    except BaseException:
        _clear(handle)
        raise

    if token is _ABORTED or token is _TIMEOUT:
        _clear(handle)
        raise AuthCancelledError("Sign-in was not completed. Re-run the cell to try again.")

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


# Sentinel distinguishing "timed out" from "still waiting" in the poll loop.
_TIMEOUT = object()

# Sentinel for a terminal widget outcome (sign-in cancelled or failed).
_ABORTED = object()


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
