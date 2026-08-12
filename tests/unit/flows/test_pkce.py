from unittest.mock import Mock, patch

from obi_auth.flows import pkce as test_module


def test_build_auth_url():
    res = test_module._build_auth_url(
        code_challenge="foo",
        redirect_uri="bar",
        state="csrf-state",
        override_env=None,
    )
    assert res == (
        "https://staging.cell-a.openbraininstitute.org/auth/realms/SBO/protocol/openid-connect/auth"
        "?response_type=code"
        "&client_id=obi-entitysdk-auth"
        "&redirect_uri=bar"
        "&scope=openid"
        "&state=csrf-state"
        "&code_challenge=foo"
        "&code_challenge_method=S256"
        "&kc_idp_hint=github"
    )


def test_exchange_code_for_token(httpx2_mock):
    httpx2_mock.post().respond(json={"access_token": "mock-token"})
    res = test_module._exchange_code_for_token(
        code="mock-code",
        redirect_uri="mock-uri",
        code_verifier="mock-verifier",
        override_env=None,
    )
    assert res == "mock-token"


@patch("obi_auth.flows.pkce._generate_state", return_value="generated-state")
@patch("obi_auth.flows.pkce.webbrowser")
def test_authorize(mocked_webbrowser, mock_generate_state):
    mock_server = Mock()
    mock_server.redirect_uri = "http://localhost:8000/callback"
    mock_server.wait_for_code.return_value = "mock-code"

    res = test_module._authorize(
        server=mock_server,
        code_challenge="mock-challenge",
        override_env=None,
    )
    assert res == "mock-code"
    mock_server.expect_state.assert_called_once_with("generated-state")
    mocked_webbrowser.open.assert_called_once()
    opened_url = mocked_webbrowser.open.call_args.args[0]
    assert "state=generated-state" in opened_url
