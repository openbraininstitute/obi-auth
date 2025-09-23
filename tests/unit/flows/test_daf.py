from unittest.mock import patch

import pytest

from obi_auth.exception import AuthFlowError
from obi_auth.flows import daf as test_module
from obi_auth.typedef import AuthDeviceInfo, DeploymentEnvironment


@pytest.fixture
def device_info():
    return AuthDeviceInfo.model_validate(
        {
            "user_code": "user_code",
            "verification_uri": "foo",
            "verification_uri_complete": "foo",
            "expires_in": 2,
            "interval": 1,
            "device_code": "bar",
        }
    )


def test_daf_authenticate(httpx_mock, device_info):
    httpx_mock.add_response(method="POST", json=device_info.model_dump(mode="json"))
    httpx_mock.add_response(
        method="POST",
        json={
            "access_token": "token",
        },
    )
    res = test_module.daf_authenticate(environment=DeploymentEnvironment.staging)
    assert res == "token"


def test_device_code_token(httpx_mock, device_info):
    httpx_mock.add_response(method="POST", json={"access_token": "foo"})

    res = test_module._get_device_code_token(device_info, None)
    assert res == "foo"

    httpx_mock.add_response(method="POST", status_code=400, json={"error": "authorization_pending"})
    res = test_module._get_device_code_token(device_info, None)
    assert res is None


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token(mock_code_token_method, device_info):
    mock_code_token_method.return_value = None

    device_info.expires_in = 1
    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_device_code_token(device_info, None)
