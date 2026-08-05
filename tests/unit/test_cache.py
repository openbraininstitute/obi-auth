from unittest.mock import Mock

import jwt
import pytest
from cryptography.fernet import Fernet

from obi_auth import cache as test_module
from obi_auth.typedef import (
    AuthManagerTokenInfo,
    CachedAuthManagerTokenInfo,
    CachedTokenInfo,
    KeycloakTokenInfo,
)
from obi_auth.util import derive_fernet_key

CIPHER = Fernet(key=derive_fernet_key())


@pytest.fixture(scope="module")
def issued_at():
    return test_module._now()


@pytest.fixture(scope="module")
def expires_at(issued_at):
    return issued_at + 3600


@pytest.fixture(scope="module")
def token_decoded(issued_at, expires_at):
    return {
        "exp": expires_at,
        "iat": issued_at,
    }


@pytest.fixture(scope="module")
def token(token_decoded):
    return jwt.encode(token_decoded, key=None, algorithm="none")


@pytest.fixture
def token_expired(token_decoded):
    data = token_decoded.copy()
    data["exp"] = test_module._now() - 1
    return jwt.encode(data, key=None, algorithm="none")


def test_token_cache(token):
    storage = Mock()
    cache = test_module.TokenCache()

    # if no stored token get returns None
    storage.read.return_value = None
    assert cache.get(storage) is None

    # set a valid token
    token_info = KeycloakTokenInfo(access_token=token)
    cache.set(token_info, storage)

    # grab the stored token from the mock
    (cached_token_info,), _ = storage.write.call_args
    assert isinstance(cached_token_info, CachedTokenInfo)

    # get the valid token
    storage.read.return_value = cached_token_info

    # fetch and decrypt the token
    res = cache.get(storage)
    assert res == KeycloakTokenInfo(access_token=token)


def test_token_cache__expired(token_expired):
    storage = Mock()
    cache = test_module.TokenCache()
    cache.set(KeycloakTokenInfo(access_token=token_expired), storage)

    (cached_token_info,), _ = storage.write.call_args

    storage.exists.return_value = True
    storage.read.return_value = cached_token_info

    res = cache.get(storage)
    assert res is None
    storage.clear.assert_called_once()


def test_token_cache__wrong_stored_type(token):
    storage = Mock()
    cache = test_module.TokenCache()
    storage.read.return_value = CachedAuthManagerTokenInfo(
        token=b"x", ttl=1, persistent_token_id=b"y"
    )
    assert cache.get(storage) is None
    storage.clear.assert_called_once()


def test_auth_manager_token_cache(token):
    storage = Mock()
    cache = test_module.AuthManagerTokenCache()

    token_info = AuthManagerTokenInfo(
        access_token=token,
        persistent_token_id="persistent-id",  # noqa: S106
    )
    cache.set(token_info, storage)

    (cached_token_info,), _ = storage.write.call_args
    assert isinstance(cached_token_info, CachedAuthManagerTokenInfo)

    storage.read.return_value = cached_token_info
    assert cache.get(storage) == token_info


def test_auth_manager_token_cache__expired_returns_persistent_id(token_expired):
    storage = Mock()
    cache = test_module.AuthManagerTokenCache()

    cache.set(
        AuthManagerTokenInfo(
            access_token=token_expired,
            persistent_token_id="persistent-id",  # noqa: S106
        ),
        storage,
    )

    (cached_token_info,), _ = storage.write.call_args
    storage.read.return_value = cached_token_info

    res = cache.get(storage)
    assert res == AuthManagerTokenInfo(
        access_token=None,
        persistent_token_id="persistent-id",  # noqa: S106
    )
    storage.clear.assert_not_called()


def test_auth_manager_token_cache__wrong_stored_type():
    storage = Mock()
    cache = test_module.AuthManagerTokenCache()
    storage.read.return_value = CachedTokenInfo(token=b"x", ttl=1)
    assert cache.get(storage) is None
    storage.clear.assert_called_once()


def test_auth_manager_token_cache__missing_storage():
    storage = Mock()
    cache = test_module.AuthManagerTokenCache()
    storage.read.return_value = None
    assert cache.get(storage) is None


def test_auth_manager_token_cache__invalid_persistent_id(token):
    storage = Mock()
    cache = test_module.AuthManagerTokenCache()
    cache.set(
        AuthManagerTokenInfo(
            access_token=token,
            persistent_token_id="persistent-id",  # noqa: S106
        ),
        storage,
    )
    (cached_token_info,), _ = storage.write.call_args
    cached_token_info.persistent_token_id = b"invalid"

    storage.read.return_value = cached_token_info
    assert cache.get(storage) is None
    storage.clear.assert_called_once()


def test_auth_manager_token_cache__set_without_access_token():
    cache = test_module.AuthManagerTokenCache()
    with pytest.raises(ValueError, match="without an access_token"):
        cache.set(
            AuthManagerTokenInfo(access_token=None, persistent_token_id="id"),  # noqa: S106
            Mock(),
        )
