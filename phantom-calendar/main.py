"""Entry point for Phantom Calendar."""

import argparse
import sys

from auth import CREDENTIALS_FILE, get_credentials
import drive_config
from app import PhantomCalendarApp


def main():
    parser = argparse.ArgumentParser(description="Phantom Calendar")
    parser.add_argument(
        "--local-config",
        action="store_true",
        help="Override remote Drive config with local config.yaml",
    )
    args = parser.parse_args()

    if args.local_config:
        drive_config.set_local_config_mode(True)
        print("[main] Local-config mode enabled — Drive config will be ignored.")

    try:
        get_credentials()
    except FileNotFoundError:
        print(
            f"Error: credentials.json not found at {CREDENTIALS_FILE}. "
            "See README for setup instructions.",
            file=sys.stderr,
        )
        sys.exit(1)

    PhantomCalendarApp().run()


if __name__ == "__main__":
    main()
