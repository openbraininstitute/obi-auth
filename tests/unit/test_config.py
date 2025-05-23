import pytest

from obi_auth import config as test_module
from obi_auth import exception


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ENV", "staging")
    monkeypatch.setenv("KEYCLOAK_REALM", "SBO")
    return test_module.Settings()


def test_get_keycloak_url(settings):
    res = settings.get_keycloak_url()
    assert res == "https://staging.openbraininstitute.org/auth/realms/SBO"

    res = settings.get_keycloak_url(override_env="staging")
    assert res == "https://staging.openbraininstitute.org/auth/realms/SBO"

    res = settings.get_keycloak_url(override_env="production")
    assert res == "https://www.openbraininstitute.org/auth/realms/SBO"

    with pytest.raises(exception.ConfigError, match="Unknown deployment environment foo"):
        settings.get_keycloak_url(override_env="foo")


def test_get_keycloak_token_endpoint(settings):
    res = settings.get_keycloak_token_endpoint()
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"
    )

    res = settings.get_keycloak_token_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"
    )

    res = settings.get_keycloak_token_endpoint(override_env="production")
    assert res == "https://www.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/token"


def test_get_keycloak_auth_endpoint(settings):
    res = settings.get_keycloak_auth_endpoint()
    assert (
        res == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
    )

    res = settings.get_keycloak_auth_endpoint(override_env="staging")
    assert (
        res == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
    )

    res = settings.get_keycloak_auth_endpoint(override_env="production")
    assert res == "https://www.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
