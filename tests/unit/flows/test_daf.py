from unittest.mock import Mock, patch

import httpx
import pytest

from obi_auth.exception import AuthFlowError
from obi_auth.flows import daf as test_module
from obi_auth.typedef import DeploymentEnvironment


def test_daf_authenticate(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        json={
            "verification_uri_complete": "foo",
            "device_code": "bar",
        },
    )
    httpx_mock.add_response(
        method="POST",
        json={
            "access_token": "token",
        },
    )
    res = test_module.daf_authenticate(environment=DeploymentEnvironment.staging)
    assert res == "token"


def test_device_code_token(httpx_mock):
    httpx_mock.add_response(method="POST", json={"access_token": "foo"})

    res = test_module._get_device_code_token(None, None)
    assert res == "foo"


@patch("obi_auth.flows.daf._get_device_code_token")
def test_poll_device_code_token(mock_code_token_method):
    mock_code_token_method.side_effect = httpx.HTTPStatusError(
        message="foo", request=Mock(), response=Mock()
    )
    with pytest.raises(AuthFlowError, match="Polling using device code reached max retries."):
        test_module._poll_device_code_token("foo", None, interval=0.1, max_retries=1)
