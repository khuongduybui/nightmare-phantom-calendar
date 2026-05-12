"""Phantom Calendar macOS menu bar application."""

import rumps

BASE_DIR = None  # resolved in main.py; app.py itself needs no path resolution


class PhantomCalendarApp(rumps.App):
    """Menu bar application stub for Phantom Calendar."""

    def __init__(self):
        super().__init__(
            name="Phantom Calendar",
            title="⏰",
            quit_button="Quit",
        )
        self.menu = [
            rumps.MenuItem("Run now", callback=self.run_now),
        ]

    @rumps.clicked("Run now")
    def run_now(self, _):
        print("[Run now] triggered — sync not yet implemented.")
