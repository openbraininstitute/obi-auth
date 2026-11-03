import builtins
import importlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from click.testing import CliRunner

from obi_auth.cli import main
from obi_auth.typedef import AuthMode, DeploymentEnvironment, TokenProvider


def _is_click_or_cli_module(name: str) -> bool:
    return (
        name == "click"
        or name.startswith("click.")
        or name == "obi_auth.cli"
        or name.startswith("obi_auth.cli.")
    )


@contextmanager
def _without_click():
    """Temporarily pretend click (and the CLI module) are not installed."""
    real_import = builtins.__import__
    saved_modules = {
        name: module for name, module in sys.modules.items() if _is_click_or_cli_module(name)
    }

    def guarded_import(name, *args, **kwargs):
        if name == "click" or name.startswith("click."):
            raise ImportError("No module named 'click'")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = guarded_import
    for module_name in saved_modules:
        del sys.modules[module_name]
    try:
        yield
    finally:
        builtins.__import__ = real_import
        for module_name in [name for name in sys.modules if _is_click_or_cli_module(name)]:
            del sys.modules[module_name]
        sys.modules.update(saved_modules)


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_missing_cli_extra_shows_install_hint():
    """Running the CLI entry without click should explain how to install the extra."""
    with _without_click(), pytest.raises(SystemExit) as exc_info:
        importlib.import_module("obi_auth.cli")

    message = str(exc_info.value)
    assert "pip install 'obi-auth[cli]'" in message
    assert "optional dependencies" in message


def test_help(cli_runner):
    result = cli_runner.invoke(main, ["--help"])
    assert "CLI for obi-auth" in result.output
    assert result.exit_code == 0


@patch("obi_auth.get_token")
def test_get_token(mock_token, cli_runner):
    mock_token.return_value = "foo"

    result = cli_runner.invoke(main, ["get-token", "-e", "production", "-m", "daf"])
    assert result.exit_code == 0
    assert result.output == "foo\n"
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.production,
        auth_mode=AuthMode.daf,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=False,
    )

    result = cli_runner.invoke(main, ["get-token"])
    assert result.exit_code == 0
    assert result.output == "foo\n"
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=False,
    )

    result = cli_runner.invoke(main, ["get-token", "-p", "auth_manager"])
    assert result.exit_code == 0
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.auth_manager,
        persistent_token_id=None,
        offline=False,
        force_refresh=False,
    )

    result = cli_runner.invoke(
        main, ["get-token", "-m", "persistent_token", "--persistent-token-id", "pt-1"]
    )
    assert result.exit_code == 0
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.persistent_token,
        token_provider=TokenProvider.keycloak,
        persistent_token_id="pt-1",  # noqa: S106
        offline=False,
        force_refresh=False,
    )

    result = cli_runner.invoke(main, ["get-token", "-p", "auth_manager", "--offline"])
    assert result.exit_code == 0
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.auth_manager,
        persistent_token_id=None,
        offline=True,
        force_refresh=False,
    )

    result = cli_runner.invoke(main, ["get-token", "--offline"])
    assert result.exit_code == 0
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=True,
        force_refresh=False,
    )


@patch("obi_auth.get_token")
def test_get_token_force_refresh(mock_token, cli_runner):
    mock_token.return_value = "fresh-token"

    result = cli_runner.invoke(
        main, ["get-token", "-e", "production", "-m", "daf", "--force-refresh"]
    )
    assert result.exit_code == 0
    assert result.output == "fresh-token\n"
    mock_token.assert_called_with(
        environment=DeploymentEnvironment.production,
        auth_mode=AuthMode.daf,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=True,
    )


@patch("obi_auth.get_token_info")
def test_decode_token_with_argument(mock_token_info, cli_runner):
    token_info = {"sub": "user-123", "exp": 1_700_000_000}
    mock_token_info.return_value = token_info

    result = cli_runner.invoke(main, ["decode-token", "my-access-token"])

    assert result.exit_code == 0
    assert json.loads(result.output) == token_info
    assert result.output == json.dumps(token_info, indent=2) + "\n"
    mock_token_info.assert_called_once_with("my-access-token")


@patch("obi_auth.get_token_info")
def test_decode_token_from_stdin(mock_token_info, cli_runner):
    token_info = {"sub": "user-456"}
    mock_token_info.return_value = token_info

    result = cli_runner.invoke(main, ["decode-token"], input="stdin-access-token\n")

    assert result.exit_code == 0
    assert json.loads(result.output) == token_info
    mock_token_info.assert_called_once_with("stdin-access-token")


@patch("obi_auth.get_token_info")
def test_decode_token_strips_stdin_whitespace(mock_token_info, cli_runner):
    mock_token_info.return_value = {"sub": "user-789"}

    result = cli_runner.invoke(main, ["decode-token"], input="  trimmed-token  \n")

    assert result.exit_code == 0
    mock_token_info.assert_called_once_with("trimmed-token")


def test_decode_token_without_input_raises(cli_runner):
    result = cli_runner.invoke(main, ["decode-token"])

    assert result.exit_code != 0
    assert "No access token provided via argument or stdin" in result.output


@patch("obi_auth.get_user_info")
@patch("obi_auth.get_token")
def test_get_user_info(mock_token, mock_user_info, cli_runner):
    user_info = {"email": "test@example.com", "preferred_username": "tester"}
    mock_token.return_value = "access-token"
    mock_user_info.return_value = user_info

    result = cli_runner.invoke(main, ["get-user-info", "-e", "production", "-m", "daf"])

    assert result.exit_code == 0
    assert json.loads(result.output) == user_info
    assert result.output == json.dumps(user_info, indent=2) + "\n"
    mock_token.assert_called_once_with(
        environment=DeploymentEnvironment.production,
        auth_mode=AuthMode.daf,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=False,
    )
    mock_user_info.assert_called_once_with(
        "access-token", environment=DeploymentEnvironment.production
    )


@patch("obi_auth.get_user_info")
@patch("obi_auth.get_token")
def test_get_user_info_defaults(mock_token, mock_user_info, cli_runner):
    user_info = {"email": "staging@example.com"}
    mock_token.return_value = "staging-token"
    mock_user_info.return_value = user_info

    result = cli_runner.invoke(main, ["get-user-info"])

    assert result.exit_code == 0
    assert json.loads(result.output) == user_info
    mock_token.assert_called_once_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=False,
    )
    mock_user_info.assert_called_once_with(
        "staging-token", environment=DeploymentEnvironment.staging
    )


@patch("obi_auth.get_user_info")
@patch("obi_auth.get_token")
def test_get_user_info_force_refresh(mock_token, mock_user_info, cli_runner):
    user_info = {"email": "test@example.com"}
    mock_token.return_value = "fresh-token"
    mock_user_info.return_value = user_info

    result = cli_runner.invoke(main, ["get-user-info", "--force-refresh"])

    assert result.exit_code == 0
    assert json.loads(result.output) == user_info
    mock_token.assert_called_once_with(
        environment=DeploymentEnvironment.staging,
        auth_mode=AuthMode.pkce,
        token_provider=TokenProvider.keycloak,
        persistent_token_id=None,
        offline=False,
        force_refresh=True,
    )
    mock_user_info.assert_called_once_with("fresh-token", environment=DeploymentEnvironment.staging)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed")
def test_get_token_piped_to_decode_token_with_jq(tmp_path):
    """obi-auth get-token | obi-auth decode-token | jq -r '.sub'"""
    obi_auth_cli = Path(sys.executable).parent / "obi-auth"
    if not obi_auth_cli.exists():
        obi_auth_cli = shutil.which("obi-auth")
    if obi_auth_cli is None:
        pytest.skip("obi-auth CLI not installed")
    obi_auth_cli = str(obi_auth_cli)
    token = jwt.encode({"sub": "piped-user"}, key=None, algorithm="none")

    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        textwrap.dedent(
            f"""
            import obi_auth

            obi_auth.get_token = lambda **kwargs: {token!r}
            """
        )
    )

    env = os.environ.copy()
    pythonpath = [str(tmp_path)]
    if existing_pythonpath := env.get("PYTHONPATH"):
        pythonpath.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)

    get_token_cmd = [obi_auth_cli, "get-token"]
    decode_token_cmd = [obi_auth_cli, "decode-token"]
    jq_cmd = ["jq", "-r", ".sub"]

    get_token = subprocess.Popen(get_token_cmd, stdout=subprocess.PIPE, text=True, env=env)  # noqa: S603
    decode_token = subprocess.Popen(  # noqa: S603
        decode_token_cmd, stdin=get_token.stdout, stdout=subprocess.PIPE, text=True, env=env
    )
    get_token.stdout.close()
    jq = subprocess.Popen(jq_cmd, stdin=decode_token.stdout, stdout=subprocess.PIPE, text=True)  # noqa: S603
    decode_token.stdout.close()

    stdout, stderr = jq.communicate()
    decode_token.wait()
    get_token.wait()

    assert get_token.returncode == 0, stderr
    assert decode_token.returncode == 0, stderr
    assert jq.returncode == 0, stderr
    assert stdout == "piped-user\n"
