import builtins
import importlib.util

import pytest

from obi_auth import exception, widget

STAGING_REALM_URL = (
    "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect"
)
PROD_REALM_URL = "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect"

# ipyauth-pkce (and thus the real widget) is only installable on Python >= 3.12.
requires_ipyauth = pytest.mark.skipif(
    importlib.util.find_spec("ipyauth_pkce") is None,
    reason="requires the optional 'ipyauth-pkce' dependency (Python >= 3.12)",
)


@requires_ipyauth
def test_get_widget_defaults():
    w = widget.get_widget(redirect_uri="http://localhost:8888/callback/")

    # Returned object is an ipyauth_pkce Auth widget.
    assert type(w).__name__ == "Auth"

    params = w.params
    assert params["name"] == "keycloak"
    assert params["authorize_endpoint"] == f"{STAGING_REALM_URL}/auth"
    assert params["token_endpoint"] == f"{STAGING_REALM_URL}/token"

    url_params = params["url_params"]
    assert url_params["response_type"] == "code"
    assert url_params["client_id"] == "obi-entitysdk-auth"
    assert url_params["redirect_uri"] == "http://localhost:8888/callback/"
    assert url_params["scope"] == "openid profile"


def test_obi_logo_bytes_is_valid_svg():
    data = widget._obi_logo_bytes()
    assert isinstance(data, bytes)
    assert data.lstrip().startswith(b"<svg")
    assert b"</svg>" in data


@requires_ipyauth
def test_get_widget_uses_obi_logo():
    w = widget.get_widget(redirect_uri="http://localhost:8888/callback/")

    def descendants(node):
        for child in getattr(node, "children", ()):
            yield child
            yield from descendants(child)

    image = next(x for x in descendants(w) if type(x).__name__ == "Image")
    assert image.format == "svg+xml"
    assert bytes(image.value) == widget._obi_logo_bytes()


@requires_ipyauth
def test_get_widget_falls_back_without_logo_support(monkeypatch):
    # Simulate an older ipyauth-pkce whose Auth(...) rejects the logo kwarg.
    import ipyauth_pkce

    real_auth = ipyauth_pkce.Auth

    def auth_without_logo(*args, logo=None, **kwargs):
        if logo is not None:
            raise TypeError("unexpected keyword argument 'logo'")
        return real_auth(*args, **kwargs)

    monkeypatch.setattr(ipyauth_pkce, "Auth", auth_without_logo)

    w = widget.get_widget(redirect_uri="http://localhost:8888/callback/")
    assert type(w).__name__ == "Auth"


@requires_ipyauth
def test_get_widget_production_and_overrides():
    w = widget.get_widget(
        redirect_uri="http://localhost:8888/callback/",
        environment="production",
        client_id="custom-client",
        scope="openid profile email",
    )

    params = w.params
    assert params["authorize_endpoint"] == f"{PROD_REALM_URL}/auth"
    assert params["url_params"]["client_id"] == "custom-client"
    assert params["url_params"]["scope"] == "openid profile email"


def test_get_widget_missing_dependency(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ipyauth_pkce":
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(exception.ClientError, match="pip install obi-auth\\[notebook\\]"):
        widget.get_widget(redirect_uri="http://localhost:8888/callback/")
