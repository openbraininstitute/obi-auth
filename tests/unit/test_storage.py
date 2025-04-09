import pytest

from obi_auth import storage as test_module
from obi_auth.typedef import TokenInfo


@pytest.fixture
def path(tmp_path):
    return tmp_path / "foo.json"


def test_storage__empty(path):
    storage = test_module.Storage(path)
    assert storage.empty()
    path.write_text("foo")
    assert not storage.empty()


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
    assert storage.empty()

    # nothing should happen
    storage.clear()
