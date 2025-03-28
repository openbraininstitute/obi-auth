from unittest.mock import Mock, patch

from obi_auth import flow as test_module


def test_build_auth_url():
    res = test_module._build_auth_url(
        code_challenge="foo",
        redirect_uri="bar",
        override_env=None,
    )
    assert res == (
        "https://staging.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
        "?response_type=code"
        "&client_id=obi-entitysdk-auth"
        "&redirect_uri=bar"
        "&scope=openid"
        "&code_challenge=foo"
        "&code_challenge_method=S256"
        "&kc_idp_hint=github"
    )


def test_exchange_code_for_token(httpx_mock):
    httpx_mock.add_response(method="POST", json={"access_token": "mock-token"})
    res = test_module._exchange_code_for_token(
        code="mock-code",
        redirect_uri="mock-uri",
        code_verifier="mock-verifier",
        override_env=None,
    )
    assert res == "mock-token"


@patch("obi_auth.flow.webbrowser")
def test_authorize(mocked_webbrowser):
    mock_server = Mock()
    mock_server.wait_for_code.return_value = "mock-code"

    res = test_module._authorize(
        server=mock_server,
        code_challenge="mock-challenge",
        override_env=None,
    )
    assert res == "mock-code"
