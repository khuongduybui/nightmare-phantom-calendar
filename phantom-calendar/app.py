"""Phantom Calendar macOS menu bar application."""

import sys

import rumps

from drive_config import parse_config, read_config
from scheduler import check_and_run_missed_sync, start_scheduler
from sync_job import run_nightly_sync


class PhantomCalendarApp(rumps.App):
    """Menu bar application with nightly sync scheduler."""

    def __init__(self):
        super().__init__(
            name="Phantom Calendar",
            title="⏰",
            quit_button="Quit",
        )
        self.menu = [
            rumps.MenuItem("Run now", callback=self.run_now),
        ]

        # Load config once at startup to get timezone for scheduler
        try:
            config = parse_config(read_config())
            timezone_str = config.get("timezone", "America/New_York")
        except Exception as exc:
            print(f"[app] WARNING: Could not load config at startup — {exc}", file=sys.stderr)
            timezone_str = "America/New_York"

        # Run a missed sync if 9pm has already passed today
        check_and_run_missed_sync(timezone_str)

        # Start the background scheduler
        self._scheduler = start_scheduler(timezone_str)

    def __del__(self):
        if hasattr(self, "_scheduler") and self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass

    @rumps.clicked("Run now")
    def run_now(self, _):
        import threading
        threading.Thread(target=run_nightly_sync, daemon=True).start()
