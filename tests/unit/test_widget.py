import builtins
import importlib.util

import pytest

from obi_auth import exception, widget

STAGING_REALM_URL = (
    "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect"
)
PROD_REALM_URL = "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect"

# The real widget can only be built when the optional ipyauth-pkce dependency is
# installed, which requires Python >= 3.12 (see the notebook extra markers).
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
