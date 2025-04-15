import os
import stat

import pytest

from obi_auth import storage as test_module
from obi_auth.storage import ENV_TO_FILE_NAME
from obi_auth.typedef import DeploymentEnvironment, TokenInfo

PROD = DeploymentEnvironment.production
STAGING = DeploymentEnvironment.staging


def get_unix_permissions(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.fixture
def config_dir(tmp_path):
    return tmp_path / "dir"


def test_storage_init__no_dir(config_dir):
    assert not config_dir.exists()

    test_module.Storage(config_dir, STAGING)
    assert config_dir.exists()

    # check that directory created with correct permissions
    assert get_unix_permissions(config_dir) == 0o700

    test_module.Storage(config_dir, PROD)
    assert config_dir.exists()

    # check that directory created with correct permissions
    assert get_unix_permissions(config_dir) == 0o700


def test_storage_init__existing_dir(config_dir):
    config_dir.mkdir()

    assert get_unix_permissions(config_dir) != 0o700

    storage = test_module.Storage(config_dir, "staging")
    assert config_dir.exists()

    assert get_unix_permissions(config_dir) == 0o700

    expected_file = config_dir / ENV_TO_FILE_NAME[STAGING]
    assert storage._file_path == expected_file

    # not written yet
    assert not storage.exists()


def test_storage__empty(config_dir):
    storage = test_module.Storage(config_dir, STAGING)
    assert not storage.exists()
    storage._file_path.write_text("foo")
    assert storage.exists()


def test_storage__read(config_dir):
    obj = TokenInfo(token=b"foo", ttl=100)

    storage = test_module.Storage(config_dir, STAGING)

    res = storage.read()
    assert res is None

    storage._file_path.write_text(obj.model_dump_json())

    res = storage.read()
    assert res == obj

    storage2 = test_module.Storage(config_dir, STAGING)
    res = storage2.read()
    assert res == obj

    storage3 = test_module.Storage(config_dir, PROD)
    assert not storage3.exists()


def test_storage__write(config_dir):
    storage = test_module.Storage(config_dir, PROD)
    obj = TokenInfo(token=b"foo", ttl=100)
    storage.write(obj)
    res = TokenInfo.model_validate_json(storage._file_path.read_bytes())
    assert res == obj

    obj2 = TokenInfo(token=b"bar", ttl=100)
    storage.write(obj2)
    res = TokenInfo.model_validate_json(storage._file_path.read_bytes())
    assert res == obj2


def test_storage__clear(config_dir):
    storage = test_module.Storage(config_dir, PROD)

    storage._file_path.write_text("foo")
    assert storage.exists()

    storage.clear()

    assert not storage._file_path.exists()
    assert not storage.exists()

    # nothing should happen
    storage.clear()


def test_file_permissions(config_dir):
    existing = test_module.Storage(config_dir, STAGING)._file_path
    existing.touch()
    existing.chmod(mode=0o777)
    assert get_unix_permissions(existing) == 0o777

    storage = test_module.Storage(config_dir, STAGING)
    assert get_unix_permissions(storage._file_path) != 0o600

    storage.write(TokenInfo(token=b"bar", ttl=100))
    assert get_unix_permissions(storage._file_path) == 0o600

    storage.clear()
    storage.write(TokenInfo(token=b"bar", ttl=100))
    assert get_unix_permissions(storage._file_path) == 0o600
