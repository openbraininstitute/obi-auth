from unittest.mock import Mock

import jwt
import pytest
from cryptography.fernet import Fernet

from obi_auth import cache as test_module
from obi_auth.config import settings

CIPHER = Fernet(key=settings.secret_key)


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
    cache = test_module.TokenCache(storage=storage)

    # if no stored token get returns None
    storage.empty.return_value = True
    assert cache.get() is None

    # set a valid token
    cache.set(token)

    # grab the stored token from the mock
    (token_info,), _ = storage.write.call_args

    # get the valid token
    storage.empty.return_value = False
    storage.read.return_value = token_info

    # fetch and decrypt the token
    res = cache.get()
    assert res == token


def test_token_cache__expired(token_expired):
    storage = Mock()
    cache = test_module.TokenCache(storage=storage)
    cache.set(token_expired)

    (token_info,), _ = storage.write.call_args

    storage.empty.return_value = False
    storage.read.return_value = token_info

    res = cache.get()
    assert res is None
    storage.clear.assert_called_once()
