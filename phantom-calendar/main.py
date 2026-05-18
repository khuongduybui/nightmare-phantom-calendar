"""Entry point for Phantom Calendar."""

import argparse
import logging
import os
import sys

from auth import CREDENTIALS_FILE, get_credentials
import drive_config
from app import PhantomCalendarApp

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Bootstrap root logging. DEBUG output enabled via PHANTOM_DEBUG=1."""
    level = logging.DEBUG if os.environ.get("PHANTOM_DEBUG") == "1" else logging.INFO
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    configure_logging()

    parser = argparse.ArgumentParser(description="Phantom Calendar")
    parser.add_argument(
        "--local-config",
        action="store_true",
        help="Override remote Drive config with local config.yaml",
    )
    args = parser.parse_args()

    if args.local_config:
        drive_config.set_local_config_mode(True)
        logger.info("Local-config mode enabled — Drive config will be ignored.")

    try:
        get_credentials()
    except FileNotFoundError:
        logger.error(
            "credentials.json not found at %s. See README for setup instructions.",
            CREDENTIALS_FILE,
        )
        sys.exit(1)

    PhantomCalendarApp().run()


if __name__ == "__main__":
    main()
