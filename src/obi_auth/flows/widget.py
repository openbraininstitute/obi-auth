"""Interactive notebook widget authentication flow (auth_mode="widget").

This flow renders an ``ipyauth-pkce`` sign-in widget in the notebook cell and
blocks until the user signs in, then returns the resulting Keycloak access
token. This lets notebooks keep the synchronous
``token = get_token(..., auth_mode="widget")`` contract and only change the
``auth_mode`` argument.

Blocking a cell while still processing the widget's frontend comm messages
(and *not* prematurely running the cells below, so ``Run All`` keeps working)
is handled by ``jupyter-ui-poll``.
"""

import logging
import time

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.typedef import DeploymentEnvironment, KeycloakTokenInfo
from obi_auth.util import is_running_in_notebook
from obi_auth.widget import get_widget

L = logging.getLogger(__name__)

_MISSING_POLL_MSG = (
    "The notebook widget auth mode requires the optional 'jupyter-ui-poll' "
    "dependency. Install it with: pip install obi-auth[notebook]"
)

_POLL_SLEEP_SECONDS = 0.1


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
            "auth_mode='widget' is only supported inside a Jupyter notebook. "
            "Use auth_mode='pkce' or auth_mode='daf' from a terminal or script."
        )

    try:
        from jupyter_ui_poll import run_ui_poll_loop  # ty: ignore[unresolved-import]
    except ImportError as exc:
        raise AuthFlowError(_MISSING_POLL_MSG) from exc

    widget = get_widget(environment=environment)
    _display(widget)

    deadline = time.monotonic() + settings.WIDGET_TIMEOUT_SECONDS

    def _check():
        # Returning None keeps the poll loop running (while still servicing
        # widget comm events); returning a value stops it.
        if widget.access_token:
            return widget.access_token
        if time.monotonic() >= deadline:
            return _TIMEOUT
        return None

    token = run_ui_poll_loop(_check, sleep=_POLL_SLEEP_SECONDS)
    if token is _TIMEOUT:
        raise AuthFlowError("Widget sign-in timed out before a token was received.")

    return KeycloakTokenInfo(access_token=token)


# Sentinel distinguishing "timed out" from "still waiting" in the poll loop.
_TIMEOUT = object()


def _display(widget) -> None:
    """Display the widget in the current notebook cell."""
    from IPython.display import display  # ty: ignore[unresolved-import]

    display(widget)
