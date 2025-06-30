import pytest

from obi_auth.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ENV", "staging")
    monkeypatch.setenv("KEYCLOAK_REALM", "SBO")
    return Settings()
