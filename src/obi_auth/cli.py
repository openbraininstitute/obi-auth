#!/bin/env python3
"""CLI for obi-auth."""

import logging
import pprint

import click

import obi_auth
from obi_auth.typedef import AuthMode, DeploymentEnvironment


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="WARNING",
    show_default=True,
    help="Logging level",
)
def main(log_level):
    """CLI for obi-auth."""
    logging.basicConfig(level=log_level)


@main.command()
@click.option("--environment", "-e", default="staging", help="The person to greet")
@click.option(
    "--auth-mode",
    "-m",
    default="pkce",
    help="Authentication method",
    type=click.Choice([mode.value for mode in AuthMode]),
)
@click.option("--show-decoded", help="Show decoded information", is_flag=True, default=False)
@click.option("--show-user-info", help="Show user info information", is_flag=True, default=False)
def get_token(environment, auth_mode, show_decoded, show_user_info):
    """Authenticate, print the token to stdout."""
    environment = DeploymentEnvironment(environment)

    access_token = obi_auth.get_token(environment=environment, auth_mode=AuthMode(auth_mode))
    print(access_token)

    if show_decoded:
        pprint.pprint(obi_auth.get_token_info(access_token))

    if show_user_info:
        pprint.pprint(obi_auth.get_user_info(access_token, environment=environment))
