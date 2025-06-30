from unittest.mock import patch

import pytest
from click.testing import CliRunner

from obi_auth.cli import main


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_help(cli_runner):
    result = cli_runner.invoke(main, ["--help"])
    assert "CLI for obi-auth" in result.output
    assert result.exit_code == 0


@patch("obi_auth.get_user_info")
@patch("obi_auth.get_token_info")
@patch("obi_auth.get_token")
def test_get_token(mock_token, mock_info, mock_user, cli_runner):
    mock_token.return_value = "foo"
    mock_info.return_value = "bar"
    mock_user.return_value = "zee"

    result = cli_runner.invoke(main, ["get-token", "-e", "production", "-m", "daf"])
    assert result.output == "foo\n"

    result = cli_runner.invoke(
        main, ["get-token", "-e", "production", "-m", "daf", "--show-decoded"]
    )
    assert "foo" in result.output
    assert "bar" in result.output

    result = cli_runner.invoke(
        main, ["get-token", "-e", "production", "-m", "daf", "--show-user-info"]
    )
    assert "foo" in result.output
    assert "zee" in result.output

    result = cli_runner.invoke(
        main, ["get-token", "-e", "production", "-m", "daf", "--show-decoded", "--show-user-info"]
    )
    assert "foo" in result.output
    assert "bar" in result.output
    assert "zee" in result.output
