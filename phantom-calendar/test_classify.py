#!/usr/bin/env python3
"""Test script: classify a calendar event using the osaurus local AI server.

Uses the same osaurus_client code path as the production sync popup.

Usage:
    uv run test_classify.py
    uv run test_classify.py --title "Team retrospective" --description "Quarterly retro with the full team"
"""

import sys

import click
import yaml

import osaurus_client

CONFIG_YAML = "config.yaml"


def load_categories(config_path: str) -> list[str]:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return list((config.get("meeting_type_prep") or {}).keys())


@click.command()
@click.option("--title", prompt="Event title", help="Event title")
@click.option(
    "--description",
    default="",
    prompt="Event description (optional)",
    prompt_required=False,
    help="Event description",
)
@click.option(
    "--timeout",
    default=3.0,
    show_default=True,
    help="HTTP timeout in seconds for the osaurus request",
)
def main(title: str, description: str, timeout: float):
    """Classify a calendar event via osaurus (same code path as the sync popup)."""
    categories = load_categories(CONFIG_YAML)

    result = osaurus_client.suggest_meeting_type(
        title, description, categories, timeout=timeout
    )

    if result is None:
        click.echo(
            "(no suggestion — osaurus unavailable or response unrecognised)", err=True
        )
        sys.exit(1)

    click.echo(result)


if __name__ == "__main__":
    main()
