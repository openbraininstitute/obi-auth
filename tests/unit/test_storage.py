import os
import stat

import pytest

from obi_auth import storage as test_module
from obi_auth.typedef import TokenInfo


def get_unix_permissions(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "foo.json"


def test_storage__empty(path):
    storage = test_module.Storage(path)
    assert not storage.exists()
    path.write_text("foo")
    assert storage.exists()


def test_storage__read(path):
    obj = TokenInfo(token=b"foo", ttl=100)
    path.write_text(obj.model_dump_json())

    res = test_module.Storage(path).read()
    assert res == obj


def test_storage__write(path):
    storage = test_module.Storage(path)
    obj = TokenInfo(token=b"foo", ttl=100)
    storage.write(obj)
    res = TokenInfo.model_validate_json(path.read_bytes())
    assert res == obj

    obj2 = TokenInfo(token=b"bar", ttl=100)
    storage.write(obj2)
    res = TokenInfo.model_validate_json(path.read_bytes())
    assert res == obj2


def test_storage__clear(path):
    path.write_text("foo")
    assert path.exists()

    storage = test_module.Storage(path)

    storage.clear()

    assert not path.exists()
    assert not storage.exists()

    # nothing should happen
    storage.clear()


def test_file_permissions(tmp_path):
    existing = tmp_path / "foo.json"
    existing.touch()
    existing.chmod(mode=0o777)
    assert get_unix_permissions(existing) == 0o777

    storage = test_module.Storage(existing)
    assert get_unix_permissions(storage.file_path) == 0o600

    storage.write(TokenInfo(token=b"bar", ttl=100))
    assert get_unix_permissions(storage.file_path) == 0o600

    storage.clear()
    storage.write(TokenInfo(token=b"bar", ttl=100))
    assert get_unix_permissions(storage.file_path) == 0o600
