"""osaurus_client — thin wrapper around the local osaurus AI server.

Provides suggest_meeting_type() for use by the sync popup classification flow.
Never call this module from scheduler.py or any unattended pipeline path.
"""

import logging
import os

import yaml
from openai import OpenAI

logger = logging.getLogger(__name__)

_OSAURUS_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osaurus.yaml")
_DEFAULT_MODEL_FALLBACK = "foundation"


def _load_config() -> dict:
    """Load osaurus.yaml and return its parsed contents."""
    with open(_OSAURUS_YAML) as f:
        return yaml.safe_load(f)


def suggest_meeting_type(
    title: str,
    description: str,
    categories: list,
    timeout: float = 3.0,
) -> "str | None":
    """Ask the local osaurus server to suggest a meeting type.

    Args:
        title: Event title (sent to the model).
        description: Event description (sent to the model).
        categories: List of valid category strings from meeting_type_prep.
        timeout: HTTP timeout in seconds for the completions request.

    Returns:
        The matched category string if the model returns a valid category,
        or None on any failure (server unavailable, unrecognised response, etc.).
        Never retries.
    """
    try:
        config = _load_config()
    except Exception as exc:
        logger.warning("config load failed: %s", type(exc).__name__)
        return None

    server = (config.get("server") or "").rstrip("/")
    api_key = config.get("api_key") or ""
    model = config.get("default_module") or _DEFAULT_MODEL_FALLBACK

    category_list = "\n".join(f"- {c}" for c in categories)
    system_prompt = (
        "You are a calendar event classifier. "
        "Given an event title and description, respond with exactly one category "
        "from the list below — no explanation, no punctuation, just the category name.\n\n"
        f"Categories:\n{category_list}"
    )
    user_message = f"Title: {title}\nDescription: {description}"

    try:
        client = OpenAI(base_url=f"{server}/v1", api_key=api_key, timeout=timeout)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            max_tokens=32,
        )
        result = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("completions request failed: %s", type(exc).__name__)
        return None

    if result in categories:
        return result
    return None
