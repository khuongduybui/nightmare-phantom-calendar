"""Entry point for Phantom Calendar."""

import sys

from auth import CREDENTIALS_FILE, get_credentials
from app import PhantomCalendarApp


def main():
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
