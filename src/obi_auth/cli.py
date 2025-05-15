#!/bin/env python3
"""CLI for obi-auth."""

import logging

import click

import obi_auth


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
def get_token(environment):
    """Authenticate, print the token to stdout."""
    access_token = obi_auth.get_token(environment=environment)
    print(access_token)


if __name__ == "__main__":
    main()
