import pytest

from obi_auth import exception


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


def test_get_keycloak_device_auth_endpoint(settings):
    res = settings.get_keycloak_device_auth_endpoint()
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )

    res = settings.get_keycloak_device_auth_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )

    res = settings.get_keycloak_device_auth_endpoint(override_env="production")
    assert (
        res
        == "https://www.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth/device"
    )


def test_get_keycloak_user_info_endpoint(settings):
    res = settings.get_keycloak_user_info_endpoint()
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )

    res = settings.get_keycloak_user_info_endpoint(override_env="staging")
    assert (
        res
        == "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )

    res = settings.get_keycloak_user_info_endpoint(override_env="production")
    assert (
        res == "https://www.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/userinfo"
    )
