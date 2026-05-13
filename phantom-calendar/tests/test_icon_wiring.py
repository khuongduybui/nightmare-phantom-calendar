"""Unit tests for NPC-0009: icon wiring in app.py."""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int) -> datetime:
    d = date.today()
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


def _make_app(state_file: str | None = None):
    sf = state_file or "/tmp/test_npc9_state.json"
    with (
        patch("app.STATE_FILE", sf),
        patch("app.read_config", return_value="yaml"),
        patch("app.parse_config", return_value={"timezone": "America/New_York"}),
        patch("app.check_and_run_missed_sync"),
        patch("app.start_scheduler", return_value=MagicMock()),
        patch("app.subprocess.run", return_value=MagicMock(returncode=0)),
    ):
        return app.PhantomCalendarApp()


class TestIconWiring(unittest.TestCase):

    def setUp(self):
        self.state_file = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)

    def test_init_uses_icon_file(self):
        a = _make_app(self.state_file)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_IDLE)

    def test_init_no_emoji_title_for_icon(self):
        a = _make_app(self.state_file)
        # title should NOT be the emoji icon characters
        self.assertNotIn(a.title, ("⏰", "⏳", "⏰❌"))

    def test_set_syncing_true_shows_sync_icon(self):
        a = _make_app(self.state_file)
        a.set_syncing(True)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_SYNCING)

    def test_set_syncing_false_after_success_shows_idle(self):
        a = _make_app(self.state_file)
        a._last_sync_failed = False
        a.set_syncing(False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_IDLE)

    def test_set_syncing_false_after_error_shows_error(self):
        a = _make_app(self.state_file)
        a._last_sync_failed = True
        a.set_syncing(False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_ERROR)

    def test_update_sync_failed_shows_error_icon(self):
        a = _make_app(self.state_file)
        with patch("app.STATE_FILE", self.state_file):
            a.update_sync_state(None, failed=True)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_ERROR)

    def test_update_sync_success_shows_idle_icon(self):
        a = _make_app(self.state_file)
        with patch("app.STATE_FILE", self.state_file):
            a.update_sync_state(_dt(9, 25), failed=False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_IDLE)

    def test_load_state_error_shows_error_icon(self):
        import json

        state = {
            "last_run_time": _dt(21, 0).isoformat(),
            "last_alarm_time": None,
            "last_sync_failed": True,
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        a = _make_app(self.state_file)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_ERROR)


import app  # noqa: E402

if __name__ == "__main__":
    unittest.main()
