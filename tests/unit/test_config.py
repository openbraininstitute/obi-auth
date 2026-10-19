import pytest

from obi_auth import exception

PROD_OBI_URL = "https://cell-a.openbraininstitute.org"
STAGING_OBI_URL = "https://staging.cell-a.openbraininstitute.org"


def test_get_keycloak_base_url(settings):
    res = settings.get_keycloak_base_url()
    assert res == f"{STAGING_OBI_URL}/auth"

    res = settings.get_keycloak_base_url(override_env="staging")
    assert res == f"{STAGING_OBI_URL}/auth"

    res = settings.get_keycloak_base_url(override_env="production")
    assert res == f"{PROD_OBI_URL}/auth"

    with pytest.raises(exception.ConfigError, match="Unknown deployment environment foo"):
        settings.get_keycloak_base_url(override_env="foo")


def test_get_keycloak_url(settings):
    res = settings.get_keycloak_url()
    assert res == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO"

    res = settings.get_keycloak_url(override_env="staging")
    assert res == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO"

    res = settings.get_keycloak_url(override_env="production")
    assert res == "https://cell-a.openbraininstitute.org/auth/realms/SBO"

    with pytest.raises(exception.ConfigError, match="Unknown deployment environment foo"):
        settings.get_keycloak_url(override_env="foo")


def test_get_keycloak_token_endpoint(settings):
    res = settings.get_keycloak_token_endpoint()
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"
    )

    res = settings.get_keycloak_token_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"
    )

    res = settings.get_keycloak_token_endpoint(override_env="production")
    assert (
        res == "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"
    )


def test_get_keycloak_auth_endpoint(settings):
    res = settings.get_keycloak_auth_endpoint()
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
    )

    res = settings.get_keycloak_auth_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
    )

    res = settings.get_keycloak_auth_endpoint(override_env="production")
    assert (
        res == "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
    )


def test_get_keycloak_device_auth_endpoint(settings):
    res = settings.get_keycloak_device_auth_endpoint()
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )

    res = settings.get_keycloak_device_auth_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )

    res = settings.get_keycloak_device_auth_endpoint(override_env="production")
    assert (
        res
        == "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )


def test_get_keycloak_user_info_endpoint(settings):
    res = settings.get_keycloak_user_info_endpoint()
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )

    res = settings.get_keycloak_user_info_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )

    res = settings.get_keycloak_user_info_endpoint(override_env="production")
    assert (
        res
        == "https://cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )


def test_get_auth_manager_url(settings):
    res = settings.get_auth_manager_url()
    assert res == f"{STAGING_OBI_URL}/api/auth-manager/v1"

    res = settings.get_auth_manager_url(override_env="staging")
    assert res == f"{STAGING_OBI_URL}/api/auth-manager/v1"

    res = settings.get_auth_manager_url(override_env="production")
    assert res == f"{PROD_OBI_URL}/api/auth-manager/v1"

    with pytest.raises(exception.ConfigError, match="Unknown deployment environment foo"):
        settings.get_auth_manager_url(override_env="foo")


def test_get_auth_manager_token_exchange_endpoint(settings):
    res = settings.get_auth_manager_token_exchange_endpoint()
    assert res == f"{STAGING_OBI_URL}/api/auth-manager/v1/token-exchange"

    res = settings.get_auth_manager_token_exchange_endpoint(override_env="production")
    assert res == f"{PROD_OBI_URL}/api/auth-manager/v1/token-exchange"


def _settings_without_jupyter_env(monkeypatch):
    # Ensure a clean environment for redirect-uri resolution tests.
    for var in (
        "OBI_AUTH_WIDGET_REDIRECT_URI",
        "OBI_AUTH_WIDGET_PUBLIC_HOST",
        "JUPYTERHUB_SERVICE_PREFIX",
    ):
        monkeypatch.delenv(var, raising=False)
    from obi_auth.config import Settings

    return Settings()


def test_resolve_widget_redirect_uri_explicit_argument(monkeypatch):
    s = _settings_without_jupyter_env(monkeypatch)
    assert s.resolve_widget_redirect_uri("https://example.org/cb/") == "https://example.org/cb/"


def test_resolve_widget_redirect_uri_from_setting(monkeypatch):
    monkeypatch.setenv("OBI_AUTH_WIDGET_REDIRECT_URI", "https://configured.example.org/callback/")
    monkeypatch.delenv("OBI_AUTH_WIDGET_PUBLIC_HOST", raising=False)
    monkeypatch.setenv("JUPYTERHUB_SERVICE_PREFIX", "/user/alice/server1/")
    from obi_auth.config import Settings

    s = Settings()
    # Explicit setting wins over derivation.
    assert s.resolve_widget_redirect_uri() == "https://configured.example.org/callback/"


def test_resolve_widget_redirect_uri_derived_from_prefix(monkeypatch):
    monkeypatch.delenv("OBI_AUTH_WIDGET_REDIRECT_URI", raising=False)
    monkeypatch.setenv("OBI_AUTH_WIDGET_PUBLIC_HOST", "https://jupyterhub.example.org/")
    monkeypatch.setenv("JUPYTERHUB_SERVICE_PREFIX", "/user/alice/19948fcb4b66cf8/")
    from obi_auth.config import Settings

    s = Settings()
    assert (
        s.resolve_widget_redirect_uri()
        == "https://jupyterhub.example.org/user/alice/19948fcb4b66cf8/callback/"
    )


def test_resolve_widget_redirect_uri_default_fallback(monkeypatch):
    # Public host set but no Jupyter prefix -> fall back to localhost default.
    monkeypatch.delenv("OBI_AUTH_WIDGET_REDIRECT_URI", raising=False)
    monkeypatch.setenv("OBI_AUTH_WIDGET_PUBLIC_HOST", "https://jupyterhub.example.org")
    monkeypatch.delenv("JUPYTERHUB_SERVICE_PREFIX", raising=False)
    from obi_auth.config import Settings

    s = Settings()
    assert s.resolve_widget_redirect_uri() == "http://localhost:8888/callback/"
