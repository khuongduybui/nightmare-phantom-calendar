#!/usr/bin/env python3
"""Test script: classify a calendar event using the osaurus local AI server.

Usage:
    uv run test_classify.py
    uv run test_classify.py --title "Team retrospective" --description "Quarterly retro with the full team"
"""

import sys

import click
import yaml
from openai import OpenAI

OSAURUS_YAML = "osaurus.yaml"
CONFIG_YAML = "config.yaml"


def load_osaurus_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_categories(config_path: str) -> list[str]:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return list((config.get("meeting_type_prep") or {}).keys())


def classify_event(
    title: str, description: str, categories: list[str], client: OpenAI, model: str
) -> str:
    category_list = "\n".join(f"- {c}" for c in categories)
    system_prompt = (
        "You are a calendar event classifier. "
        "Given an event title and description, respond with exactly one category from the list below — "
        "no explanation, no punctuation, just the category name.\n\n"
        f"Categories:\n{category_list}"
    )
    user_prompt = f"Title: {title}\nDescription: {description}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=32,
    )
    return response.choices[0].message.content.strip()


def pick_model(client: OpenAI, default_model: str) -> str:
    models = client.models.list()
    ids = [m.id for m in models.data]
    if not ids:
        print("ERROR: no models available on the osaurus server.", file=sys.stderr)
        sys.exit(1)
    if default_model in ids:
        return default_model
    if len(ids) > 1:
        print("Available models:")
        for i, m in enumerate(ids):
            print(f"  [{i}] {m}")
        choice = input(f"Select model [0]: ").strip()
        idx = int(choice) if choice else 0
        return ids[idx]
    return ids[0]


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
    "--model", default=None, help="Model ID to use (auto-selected if omitted)"
)
def main(title: str, description: str, model: str | None):
    """Classify a calendar event via osaurus."""
    osaurus = load_osaurus_config(OSAURUS_YAML)
    server = osaurus["server"].rstrip("/")
    api_key = osaurus["api_key"]

    categories = load_categories(CONFIG_YAML)

    client = OpenAI(base_url=f"{server}/v1", api_key=api_key)

    default_model = osaurus.get("default_module", "foundation")
    model = model or pick_model(client, default_model)

    category = classify_event(title, description, categories, client, model)
    click.echo(category)


if __name__ == "__main__":
    main()
