#!/bin/env python3
"""CLI for obi-auth."""

import logging

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
@click.option(
    "--environment",
    "-e",
    default="staging",
    help="Deploymend environment",
    type=click.Choice([env.value for env in DeploymentEnvironment]),
)
@click.option(
    "--auth-mode",
    "-m",
    default="pkce",
    help="Authentication method",
    type=click.Choice([mode.value for mode in AuthMode]),
)
def get_token(environment, auth_mode):
    """Authenticate, print the token to stdout."""
    access_token = obi_auth.get_token(environment=environment, auth_mode=auth_mode)
    print(access_token)


if __name__ == "__main__":
    main()
