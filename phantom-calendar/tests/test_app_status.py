"""Unit tests for app.py status display and login item registration."""

import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, patch as mock_patch

import pytz


LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int) -> datetime:
    d = date.today()
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


def _make_app():
    """Create a PhantomCalendarApp with all external dependencies mocked."""
    with (
        patch("app.read_config", return_value="yaml"),
        patch("app.parse_config", return_value={"timezone": "America/New_York"}),
        patch("app.check_and_run_missed_sync"),
        patch("app.start_scheduler", return_value=MagicMock()),
        patch("app.subprocess.run", return_value=MagicMock(returncode=0)),
        # Patch icon constants to None so rumps doesn't try to load the PNG files
        patch.object(app.PhantomCalendarApp, "ICON_IDLE", None),
        patch.object(app.PhantomCalendarApp, "ICON_SYNCING", None),
        patch.object(app.PhantomCalendarApp, "ICON_ERROR", None),
        # Use nonexistent state file so _load_state is a no-op
        patch("app.STATE_FILE", "/tmp/nonexistent_test_state_xyz.json"),
    ):
        return app.PhantomCalendarApp()


class TestStatusMenuItems(unittest.TestCase):

    def test_initial_status_shows_placeholders(self):
        a = _make_app()
        self.assertIn("—", a._last_run_item.title)
        self.assertIn("—", a._last_alarm_item.title)

    def test_update_sync_state_updates_last_run_item(self):
        a = _make_app()
        alarm = _dt(9, 25)
        a.update_sync_state(alarm, failed=False)
        self.assertIn("Last run:", a._last_run_item.title)
        # Should contain a time (hours and minutes)
        self.assertRegex(a._last_run_item.title, r"\d+:\d+")

    def test_update_sync_state_updates_alarm_item(self):
        a = _make_app()
        alarm = _dt(9, 25)
        a.update_sync_state(alarm, failed=False)
        self.assertIn("Alarm:", a._last_alarm_item.title)
        self.assertIn("9:25", a._last_alarm_item.title)

    def test_update_sync_state_no_alarm(self):
        a = _make_app()
        a.update_sync_state(None, failed=False)
        self.assertEqual(a._last_alarm_item.title, "Alarm: none")

    def test_update_sync_state_failed_sets_error_icon(self):
        a = _make_app()
        a.update_sync_state(None, failed=True)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_ERROR)

    def test_update_sync_state_success_sets_normal_icon(self):
        a = _make_app()
        a.update_sync_state(_dt(9, 25), failed=False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_IDLE)

    def test_set_syncing_true_sets_spinner(self):
        a = _make_app()
        a.set_syncing(True)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_SYNCING)

    def test_set_syncing_false_restores_error_icon_when_failed(self):
        a = _make_app()
        a._last_sync_failed = True
        a.set_syncing(False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_ERROR)

    def test_set_syncing_false_restores_normal_icon_when_ok(self):
        a = _make_app()
        a._last_sync_failed = False
        a.set_syncing(False)
        self.assertEqual(a.icon, app.PhantomCalendarApp.ICON_IDLE)


class TestLoginItem(unittest.TestCase):

    def test_login_item_failure_does_not_crash_app(self):
        with (
            patch("app.read_config", return_value="yaml"),
            patch("app.parse_config", return_value={"timezone": "America/New_York"}),
            patch("app.check_and_run_missed_sync"),
            patch("app.start_scheduler", return_value=MagicMock()),
            patch("app.subprocess.run", side_effect=Exception("osascript not found")),
        ):
            # Must not raise
            a = app.PhantomCalendarApp()
            self.assertIsNotNone(a)


import app  # noqa: E402


if __name__ == "__main__":
    unittest.main()
