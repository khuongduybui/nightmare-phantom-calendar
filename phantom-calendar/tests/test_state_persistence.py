"""Unit tests for NPC-0008: state persistence across restarts."""

import json
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


def _make_app(state_file: str = "/tmp/test_phantom_state.json"):
    """Create a PhantomCalendarApp with all external dependencies mocked."""
    with (
        patch("app.STATE_FILE", state_file),
        patch("app.read_config", return_value="yaml"),
        patch("app.parse_config", return_value={"timezone": "America/New_York"}),
        patch("app.check_and_run_missed_sync"),
        patch("app.start_scheduler", return_value=MagicMock()),
        patch("app.subprocess.run", return_value=MagicMock(returncode=0)),
    ):
        return app.PhantomCalendarApp()


class TestStatePersistence(unittest.TestCase):

    def setUp(self):
        self.state_file = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)

    def test_save_state_writes_json(self):
        a = _make_app(self.state_file)
        alarm = _dt(9, 25)
        with patch("app.STATE_FILE", self.state_file):
            a.update_sync_state(alarm, failed=False)
        with open(self.state_file) as f:
            data = json.load(f)
        self.assertIn("last_run_time", data)
        self.assertIn("last_alarm_time", data)
        self.assertIn("last_sync_failed", data)
        self.assertFalse(data["last_sync_failed"])
        # alarm time should be parseable ISO string
        parsed = datetime.fromisoformat(data["last_alarm_time"])
        self.assertEqual(parsed.hour, 9)
        self.assertEqual(parsed.minute, 25)

    def test_save_state_handles_none_alarm(self):
        a = _make_app(self.state_file)
        with patch("app.STATE_FILE", self.state_file):
            a.update_sync_state(None, failed=False)
        with open(self.state_file) as f:
            data = json.load(f)
        self.assertIsNone(data["last_alarm_time"])

    def test_load_state_restores_menu_items(self):
        alarm = _dt(9, 25)
        now = _dt(21, 2)
        state = {
            "last_run_time": now.isoformat(),
            "last_alarm_time": alarm.isoformat(),
            "last_sync_failed": False,
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        a = _make_app(self.state_file)
        self.assertNotEqual(a._last_run_item.title, "Last run: —")
        self.assertNotEqual(a._last_alarm_item.title, "Alarm: —")
        self.assertIn("9:25", a._last_alarm_item.title)

    def test_load_state_sets_error_icon_on_failed(self):
        state = {
            "last_run_time": _dt(21, 0).isoformat(),
            "last_alarm_time": None,
            "last_sync_failed": True,
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        a = _make_app(self.state_file)
        self.assertEqual(a.title, "⏰❌")

    def test_load_state_missing_file_does_not_crash(self):
        # No state file — should initialize with placeholders
        a = _make_app("/tmp/nonexistent_phantom_state_xyz.json")
        self.assertEqual(a._last_run_item.title, "Last run: —")
        self.assertEqual(a._last_alarm_item.title, "Alarm: —")

    def test_load_state_corrupt_file_does_not_crash(self):
        with open(self.state_file, "w") as f:
            f.write("not valid json {{")
        a = _make_app(self.state_file)
        # Should not raise; fall back to placeholders
        self.assertEqual(a._last_run_item.title, "Last run: —")

    def test_save_state_failure_is_non_fatal(self):
        a = _make_app(self.state_file)
        with patch("app.STATE_FILE", self.state_file):
            with patch("builtins.open", side_effect=OSError("disk full")):
                # Must not raise
                a.update_sync_state(_dt(9, 25), failed=False)
        self.assertEqual(a._last_run_time.hour, datetime.now(LOCAL_TZ).hour)


import app  # noqa: E402


if __name__ == "__main__":
    unittest.main()
