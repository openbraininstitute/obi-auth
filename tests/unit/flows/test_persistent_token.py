import pytest

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.flows import persistent_token as test_module


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_persistent_token_authenticate(environment, httpx_mock):
    persistent_token_id = "mock-id"  # noqa: S105
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_access_token_endpoint(override_env=environment),
        json={"data": {"access_token": f"mock-{environment}-token"}},
        headers={"id": persistent_token_id},
    )
    res = test_module.persistent_token_authenticate(
        environment=environment, persistent_token_id=persistent_token_id
    )
    assert res == f"mock-{environment}-token"


def test_persistent_token_authenticate__raises(httpx_mock):
    persistent_token_id = "mock-id"  # noqa: S105
    httpx_mock.add_response(
        method="POST",
        url=settings.get_auth_manager_access_token_endpoint(override_env="staging"),
        headers={"id": persistent_token_id},
        json={"data": {}},
    )
    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.persistent_token_authenticate(
            environment="staging", persistent_token_id=persistent_token_id
        )
