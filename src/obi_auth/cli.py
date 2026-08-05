"""CLI for obi-auth."""

import json
import logging
import sys

import click

import obi_auth
from obi_auth.typedef import AuthMode, DeploymentEnvironment, TokenProvider


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="WARNING",
    show_default=True,
    help="Logging level",
)
def main(log_level: str):
    """CLI for obi-auth."""
    logging.basicConfig(level=log_level)


@main.command()
@click.option(
    "--environment",
    "-e",
    type=click.Choice(DeploymentEnvironment),
    default=DeploymentEnvironment.staging,
    show_default=True,
    help="Target environment",
)
@click.option(
    "--auth-mode",
    "-m",
    type=click.Choice(AuthMode),
    default=AuthMode.pkce,
    show_default=True,
    help="Authentication method",
)
@click.option(
    "--token-provider",
    "-p",
    type=click.Choice(TokenProvider),
    default=TokenProvider.keycloak,
    show_default=True,
    help="Token issuer: keycloak or auth_manager",
)
@click.option(
    "--force-refresh",
    help="Clear the cached token and authenticate again",
    is_flag=True,
    default=False,
)
def get_token(
    environment: DeploymentEnvironment,
    auth_mode: AuthMode,
    token_provider: TokenProvider,
    force_refresh: bool,
):
    """Authenticate, print the token to stdout."""
    access_token = obi_auth.get_token(
        environment=environment,
        auth_mode=auth_mode,
        token_provider=token_provider,
        force_refresh=force_refresh,
    )
    print(access_token)


@main.command()
@click.argument("access_token", required=False)
def decode_token(access_token: str | None):
    """Decode token from argument or stdin."""
    if not access_token:
        access_token = sys.stdin.read().strip()

    if not access_token:
        raise click.ClickException("No access token provided via argument or stdin")

    print(json.dumps(obi_auth.get_token_info(access_token), indent=2))


@main.command()
@click.option(
    "--environment",
    "-e",
    type=click.Choice(DeploymentEnvironment),
    default=DeploymentEnvironment.staging,
    show_default=True,
    help="Target environment",
)
@click.option(
    "--auth-mode",
    "-m",
    type=click.Choice(AuthMode),
    default=AuthMode.pkce,
    show_default=True,
    help="Authentication method",
)
@click.option(
    "--token-provider",
    "-p",
    type=click.Choice(TokenProvider),
    default=TokenProvider.keycloak,
    show_default=True,
    help="Token issuer: keycloak or auth_manager",
)
@click.option(
    "--force-refresh",
    help="Clear the cached token and authenticate again",
    is_flag=True,
    default=False,
)
def get_user_info(
    environment: DeploymentEnvironment,
    auth_mode: AuthMode,
    token_provider: TokenProvider,
    force_refresh: bool,
):
    """Show user info information."""
    access_token = obi_auth.get_token(
        environment=environment,
        auth_mode=auth_mode,
        token_provider=token_provider,
        force_refresh=force_refresh,
    )
    print(json.dumps(obi_auth.get_user_info(access_token, environment=environment), indent=2))
