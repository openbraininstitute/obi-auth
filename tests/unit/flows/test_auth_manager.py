from unittest.mock import patch

import pytest

from obi_auth.config import settings
from obi_auth.exception import AuthFlowError
from obi_auth.flows import auth_manager as test_module
from obi_auth.typedef import AuthManagerTokenInfo, KeycloakTokenInfo


def test_auth_manager_mint_access_token(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {"access_token": "minted-token"}})
    res = test_module.auth_manager_mint_access_token("persistent-id", environment="staging")
    assert res == AuthManagerTokenInfo(
        access_token="minted-token",  # noqa: S106
        persistent_token_id="persistent-id",  # noqa: S106
    )
    assert httpx2_mock.calls[0].request.headers["id"] == "persistent-id"


def test_auth_manager_mint_access_token__raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(
        AuthFlowError, match=r"AuthManager unexpected payload: \{'data': \{\}\}"
    ) as exc_info:
        test_module.auth_manager_mint_access_token("persistent-id", environment="staging")
    assert isinstance(exc_info.value.args[0], str)


def test_auth_manager_exchange_token(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {"id": "exchanged-id"}})
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {"access_token": "minted-token"}})

    res = test_module.auth_manager_exchange_token(
        KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
        environment="staging",
    )
    assert res == AuthManagerTokenInfo(
        access_token="minted-token",  # noqa: S106
        persistent_token_id="exchanged-id",  # noqa: S106
    )
    requests = [call.request for call in httpx2_mock.calls]
    assert requests[0].headers["Authorization"] == "Bearer public-token"
    assert requests[1].headers["id"] == "exchanged-id"


def test_auth_manager_exchange_token__exchange_raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(
        AuthFlowError, match=r"AuthManager unexpected payload: \{'data': \{\}\}"
    ) as exc_info:
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )
    assert isinstance(exc_info.value.args[0], str)


def test_auth_manager_exchange_token__mint_raises(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_token_exchange_endpoint(override_env="staging")
    ).respond(json={"data": {"id": "exchanged-id"}})
    httpx2_mock.post(
        settings.get_auth_manager_access_token_endpoint(override_env="staging")
    ).respond(json={"data": {}})
    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_exchange_token(
            KeycloakTokenInfo(access_token="public-token"),  # noqa: S106
            environment="staging",
        )


def test_auth_manager_get_offline_token_id(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_offline_token_id_endpoint(override_env="staging")
    ).respond(json={"data": {"persistent_token_id": "offline-id"}})

    assert (
        test_module.auth_manager_get_offline_token_id("exchanged-at", environment="staging")
        == "offline-id"
    )
    assert httpx2_mock.calls[0].request.headers["Authorization"] == "Bearer exchanged-at"


def test_auth_manager_get_offline_token_id__not_found(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_offline_token_id_endpoint(override_env="staging")
    ).respond(404, json={"error": "not found"})

    assert (
        test_module.auth_manager_get_offline_token_id("exchanged-at", environment="staging") is None
    )


def test_auth_manager_get_offline_token_id__unexpected_payload(httpx2_mock):
    httpx2_mock.post(
        settings.get_auth_manager_offline_token_id_endpoint(override_env="staging")
    ).respond(json={"data": {}})

    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_get_offline_token_id("exchanged-at", environment="staging")


def test_auth_manager_request_offline_consent(httpx2_mock):
    httpx2_mock.get(
        settings.get_auth_manager_offline_token_endpoint(override_env="staging")
    ).respond(json={"data": {"consent_url": "https://example.com/consent"}})

    assert (
        test_module.auth_manager_request_offline_consent("exchanged-at", environment="staging")
        == "https://example.com/consent"
    )
    assert httpx2_mock.calls[0].request.headers["Authorization"] == "Bearer exchanged-at"


def test_auth_manager_request_offline_consent__unexpected_payload(httpx2_mock):
    httpx2_mock.get(
        settings.get_auth_manager_offline_token_endpoint(override_env="staging")
    ).respond(json={"data": {}})

    with pytest.raises(AuthFlowError, match="AuthManager unexpected payload"):
        test_module.auth_manager_request_offline_consent("exchanged-at", environment="staging")


@patch("obi_auth.flows.auth_manager.webbrowser")
@patch("obi_auth.flows.auth_manager.sleep")
@patch("obi_auth.flows.auth_manager._display_offline_consent_prompt")
@patch(
    "obi_auth.flows.auth_manager.auth_manager_request_offline_consent",
    return_value="https://example.com/consent",
)
@patch(
    "obi_auth.flows.auth_manager.auth_manager_get_offline_token_id",
    side_effect=[None, "offline-id"],
)
def test_auth_manager_request_and_await_offline_consent(
    mock_get_id, mock_request, mock_display, mock_sleep, mock_web
):
    assert (
        test_module.auth_manager_request_and_await_offline_consent(
            "exchanged-at", environment="staging"
        )
        == "offline-id"
    )
    mock_request.assert_called_once_with("exchanged-at", environment="staging")
    mock_display.assert_called_once_with("https://example.com/consent")
    mock_web.open.assert_called_once_with("https://example.com/consent")
    mock_sleep.assert_called_once()


@patch("obi_auth.flows.auth_manager.webbrowser")
@patch("obi_auth.flows.auth_manager.sleep")
@patch("obi_auth.flows.auth_manager.monotonic", side_effect=[0, 1, 999])
@patch("obi_auth.flows.auth_manager._display_offline_consent_prompt")
@patch(
    "obi_auth.flows.auth_manager.auth_manager_request_offline_consent",
    return_value="https://example.com/consent",
)
@patch("obi_auth.flows.auth_manager.auth_manager_get_offline_token_id", return_value=None)
def test_auth_manager_request_and_await_offline_consent__timeout(
    mock_get_id, mock_request, mock_display, mock_monotonic, mock_sleep, mock_web
):
    with patch.object(settings, "OFFLINE_CONSENT_TIMEOUT_SECONDS", 10):
        with pytest.raises(AuthFlowError, match="Offline consent timed out"):
            test_module.auth_manager_request_and_await_offline_consent(
                "exchanged-at", environment="staging"
            )


@patch(
    "obi_auth.flows.auth_manager.auth_manager_mint_access_token",
    return_value=AuthManagerTokenInfo(
        access_token="offline-at",  # noqa: S106
        persistent_token_id="offline-id",  # noqa: S106
    ),
)
@patch(
    "obi_auth.flows.auth_manager.auth_manager_get_offline_token_id",
    return_value="offline-id",
)
def test_auth_manager_upgrade_to_offline_token__existing_offline(mock_get_id, mock_mint):
    res = test_module.auth_manager_upgrade_to_offline_token(
        AuthManagerTokenInfo(
            access_token="exchanged-at",  # noqa: S106
            persistent_token_id="refresh-id",  # noqa: S106
        ),
        environment="staging",
    )
    assert res.access_token == "offline-at"  # noqa: S105
    assert res.persistent_token_id == "offline-id"  # noqa: S105
    mock_get_id.assert_called_once_with("exchanged-at", environment="staging")
    mock_mint.assert_called_once_with("offline-id", environment="staging")


@patch(
    "obi_auth.flows.auth_manager.auth_manager_mint_access_token",
    return_value=AuthManagerTokenInfo(
        access_token="offline-at",  # noqa: S106
        persistent_token_id="offline-id",  # noqa: S106
    ),
)
@patch(
    "obi_auth.flows.auth_manager.auth_manager_request_and_await_offline_consent",
    return_value="offline-id",
)
@patch("obi_auth.flows.auth_manager.auth_manager_get_offline_token_id", return_value=None)
def test_auth_manager_upgrade_to_offline_token__needs_consent(mock_get_id, mock_await, mock_mint):
    res = test_module.auth_manager_upgrade_to_offline_token(
        AuthManagerTokenInfo(
            access_token="exchanged-at",  # noqa: S106
            persistent_token_id="refresh-id",  # noqa: S106
        ),
        environment="staging",
    )
    assert res.access_token == "offline-at"  # noqa: S105
    mock_await.assert_called_once_with("exchanged-at", environment="staging")
    mock_mint.assert_called_once_with("offline-id", environment="staging")


def test_auth_manager_upgrade_to_offline_token__no_access_token():
    with pytest.raises(AuthFlowError, match="did not return an access token"):
        test_module.auth_manager_upgrade_to_offline_token(
            AuthManagerTokenInfo(
                access_token=None,
                persistent_token_id="refresh-id",  # noqa: S106
            ),
            environment="staging",
        )


@patch("obi_auth.flows.auth_manager.is_running_in_notebook", return_value=False)
def test_display_offline_consent_prompt_terminal(mock_notebook, capsys):
    test_module._display_offline_consent_prompt("https://example.com/consent")
    err = capsys.readouterr().err
    assert "Offline Access Consent Required" in err
    assert "https://example.com/consent" in err


@patch("obi_auth.flows.auth_manager.is_running_in_notebook", return_value=True)
def test_display_offline_consent_prompt_notebook(mock_notebook):
    with patch("rich.console.Console") as mock_console:
        test_module._display_offline_consent_prompt("https://example.com/consent")
        mock_console.assert_called_once_with(stderr=True)
        mock_console.return_value.print.assert_called_once()


@patch("obi_auth.flows.auth_manager.is_running_in_notebook", return_value=True)
def test_display_offline_consent_prompt_notebook_fallback(mock_notebook, capsys):
    with patch("rich.console.Console", side_effect=ImportError("no rich")):
        test_module._display_offline_consent_prompt("https://example.com/consent")
    err = capsys.readouterr().err
    assert "https://example.com/consent" in err
