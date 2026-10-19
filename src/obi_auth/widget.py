"""Interactive notebook sign-in widget pre-configured for the OBI Keycloak IdP.

This module is an additive, notebook-only convenience layer on top of
`ipyauth-pkce <https://github.com/danifr/ipyauth-pkce>`_. The command-line and
scripting flows (``obi_auth.get_token`` and friends) are unaffected and keep
working without this extra installed.

``ipyauth-pkce`` is an optional dependency, installed via the ``notebook``
extra::

    pip install obi-auth[notebook]
"""

from obi_auth.config import settings
from obi_auth.exception import ClientError
from obi_auth.typedef import DeploymentEnvironment

_MISSING_DEP_MSG = (
    "The notebook widget requires the optional 'ipyauth-pkce' dependency. "
    "Install it with: pip install obi-auth[notebook]"
)


def get_widget(
    *,
    redirect_uri: str | None = None,
    environment: DeploymentEnvironment = DeploymentEnvironment.staging,
    client_id: str | None = None,
    scope: str | None = None,
):
    """Build an interactive Keycloak sign-in widget for a Jupyter notebook.

    Returns an ``ipyauth_pkce.Auth`` widget pre-configured with the OBI Keycloak
    base url, realm, and client id. Display the returned object in a notebook
    cell to render the "Sign In" button; after signing in, read the token via
    ``widget.access_token`` or the ready-to-use ``widget.headers``.

    Args:
        redirect_uri: OAuth2 redirect uri registered for the client. This is
            environment-specific (e.g. a JupyterHub callback
            ``https://.../user/<username>/<server>/callback/`` or a local
            ``http://localhost:8888/callback/``) and must be a valid url. When
            omitted, it is resolved via ``settings.resolve_widget_redirect_uri``:
            from ``OBI_AUTH_WIDGET_REDIRECT_URI`` if set, else derived from the
            running Jupyter server prefix and ``OBI_AUTH_WIDGET_PUBLIC_HOST``,
            else the local ``http://localhost:8888/callback/`` default.
        environment: Target deployment environment (``staging`` or
            ``production``). Selects the OBI Keycloak domain.
        client_id: Keycloak client id. Defaults to
            ``settings.WIDGET_CLIENT_ID``.
        scope: OAuth2 scopes. Must contain ``openid`` and ``profile``. Defaults
            to ``settings.WIDGET_SCOPE``.

    Returns:
        An ``ipyauth_pkce.Auth`` widget instance.

    Raises:
        ClientError: If the optional ``ipyauth-pkce`` dependency is not
            installed.
    """
    try:
        from ipyauth_pkce import Auth, ParamsKeycloak
    except ImportError as exc:
        raise ClientError(_MISSING_DEP_MSG) from exc

    environment = DeploymentEnvironment(environment)

    params = ParamsKeycloak(
        base_url=settings.get_keycloak_base_url(override_env=environment),
        realm=settings.KEYCLOAK_REALM,
        client_id=client_id or settings.WIDGET_CLIENT_ID,
        redirect_uri=settings.resolve_widget_redirect_uri(redirect_uri),
        scope=scope or settings.WIDGET_SCOPE,
        response_type="code",
    )
    return Auth(params=params)
