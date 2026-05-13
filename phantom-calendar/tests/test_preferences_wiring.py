"""Unit tests for NPC-0010 US-2: preferences wiring in app.py and scheduler.py."""

import json
import os
import tempfile
import threading
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz


LOCAL_TZ = pytz.timezone("America/New_York")


def _make_app(state_file: str | None = None):
    sf = state_file or "/tmp/test_npc10_state.json"
    with (
        patch("app.STATE_FILE", sf),
        patch("app.read_config", return_value="yaml"),
        patch("app.parse_config", return_value={"timezone": "America/New_York",
                                                 "daily_run_time": "21:00"}),
        patch("app.check_and_run_missed_sync"),
        patch("app.start_scheduler", return_value=MagicMock()),
        patch("app.subprocess.run", return_value=MagicMock(returncode=0)),
        patch.object(app.PhantomCalendarApp, "ICON_IDLE", None),
        patch.object(app.PhantomCalendarApp, "ICON_SYNCING", None),
        patch.object(app.PhantomCalendarApp, "ICON_ERROR", None),
        patch("app.STATE_FILE", sf),
    ):
        return app.PhantomCalendarApp()


UPDATED_PREFS = {
    "daily_run_time": "20:00",
    "timezone": "US/Pacific",
    "default_prep_minutes": 15,
    "personal_calendar_id": "new@example.com",
    "msi_calendar_id": "work2@example.com",
}


class TestPreferencesWiring(unittest.TestCase):

    def setUp(self):
        self.state_file = tempfile.mktemp(suffix=".json")

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)

    def test_preferences_menu_item_exists(self):
        a = _make_app(self.state_file)
        titles = [str(item) for item in a.menu]
        self.assertTrue(any("Preferences" in t for t in titles))

    @patch("app.PreferencesWindow")
    @patch("app.read_config", return_value="yaml")
    @patch("app.parse_config", return_value={"timezone": "America/New_York"})
    def test_show_preferences_opens_window(self, mock_parse, mock_read, mock_prefs_cls):
        a = _make_app(self.state_file)
        mock_prefs_cls.return_value.show.return_value = UPDATED_PREFS
        with patch.object(a, "_save_preferences") as mock_save:
            a.show_preferences(None)
        mock_prefs_cls.assert_called_once()
        mock_save.assert_called_once_with(UPDATED_PREFS)

    @patch("app.PreferencesWindow")
    @patch("app.read_config", return_value="yaml")
    @patch("app.parse_config", return_value={"timezone": "America/New_York"})
    def test_show_preferences_cancel_does_not_save(self, mock_parse, mock_read, mock_prefs_cls):
        a = _make_app(self.state_file)
        mock_prefs_cls.return_value.show.return_value = None
        with patch.object(a, "_save_preferences") as mock_save:
            a.show_preferences(None)
        mock_save.assert_not_called()

    @patch("app.write_config")
    @patch("app.read_config", return_value="yaml")
    @patch("app.parse_config", return_value={
        "timezone": "America/New_York",
        "daily_run_time": "21:00",
        "default_prep_minutes": 30,
        "personal_calendar_id": "old@e.com",
        "msi_calendar_id": "work@e.com",
        "baseline_event_id": "bid",
        "baseline_event_title": "Alarm",
        "baseline_event_time": "09:25",
        "recurring_meetings": [],
        "meeting_type_prep": {},
        "locations": {},
        "client_overrides": {},
    })
    def test_save_preferences_writes_to_drive(self, mock_parse, mock_read, mock_write):
        a = _make_app(self.state_file)
        with patch.object(a, "_restart_scheduler"):
            a._save_preferences(UPDATED_PREFS)
        mock_write.assert_called_once()
        written = mock_write.call_args[0][0]
        self.assertIn("US/Pacific", written)
        self.assertIn("new@example.com", written)

    def test_save_preferences_restarts_scheduler(self):
        a = _make_app(self.state_file)
        old_scheduler = MagicMock()
        a._scheduler = old_scheduler
        with (
            patch("app.write_config"),
            patch("app.read_config", return_value="yaml"),
            patch("app.parse_config", return_value={
                "timezone": "America/New_York", "daily_run_time": "21:00",
                "default_prep_minutes": 30, "personal_calendar_id": "p@e.com",
                "msi_calendar_id": "m@e.com", "baseline_event_id": "",
                "baseline_event_title": "", "baseline_event_time": "09:25",
                "recurring_meetings": [], "meeting_type_prep": {},
                "locations": {}, "client_overrides": {},
            }),
            patch("app.start_scheduler", return_value=MagicMock()) as mock_start,
        ):
            a._save_preferences(UPDATED_PREFS)
        old_scheduler.shutdown.assert_called_once_with(wait=False)
        mock_start.assert_called_once_with("US/Pacific", "20:00")

    @patch("app.PreferencesWindow")
    @patch("app.read_config", return_value="yaml")
    @patch("app.parse_config", return_value={"timezone": "America/New_York"})
    def test_double_open_prevented(self, mock_parse, mock_read, mock_prefs_cls):
        a = _make_app(self.state_file)
        mock_prefs_cls.return_value.show.return_value = None
        # Manually acquire lock to simulate already-open window
        app._PREFS_OPEN.acquire()
        try:
            a.show_preferences(None)
        finally:
            app._PREFS_OPEN.release()
        mock_prefs_cls.assert_not_called()


class TestStartSchedulerTriggerTime(unittest.TestCase):

    @patch("scheduler.CronTrigger")
    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_uses_trigger_time(self, mock_sched_cls, mock_cron_cls):
        mock_sched = MagicMock()
        mock_sched_cls.return_value = mock_sched
        scheduler.start_scheduler("America/New_York", "20:00")
        mock_cron_cls.assert_called_once_with(hour=20, minute=0, timezone="America/New_York")

    @patch("scheduler.CronTrigger")
    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_default_trigger_is_21(self, mock_sched_cls, mock_cron_cls):
        mock_sched_cls.return_value = MagicMock()
        scheduler.start_scheduler("America/New_York")
        mock_cron_cls.assert_called_once_with(hour=21, minute=0, timezone="America/New_York")


import app  # noqa: E402
import scheduler  # noqa: E402


if __name__ == "__main__":
    unittest.main()
