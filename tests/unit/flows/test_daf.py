from unittest.mock import Mock, patch

import httpx
import pytest

from obi_auth.exception import AuthFlowError
from obi_auth.flows import daf as test_module
from obi_auth.typedef import AuthDeviceInfo, DeploymentEnvironment


@pytest.fixture
def device_info():
    return AuthDeviceInfo.model_validate(
        {
            "user_code": "user_code",
            "verification_url": "foo",
            "verification_uri_complete": "foo",
            "expires_in": 600,
            "interval": 5,
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


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token(mock_code_token_method, device_info):
    mock_code_token_method.side_effect = httpx.HTTPStatusError(
        message="foo", request=Mock(), response=Mock()
    )
    device_info.interval = 1
    device_info.expires_in = 1
    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_device_code_token(device_info, None)
