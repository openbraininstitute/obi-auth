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


@patch("obi_auth.get_token")
def test_get_token(mock_token, cli_runner):
    mock_token.return_value = "foo"
    result = cli_runner.invoke(main, ["get-token", "-e", "production", "-m", "daf"])
    assert result.output == "foo\n"
