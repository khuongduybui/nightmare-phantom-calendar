"""Unit tests for sync_job.py."""

import sys
import threading
import unittest
from unittest.mock import MagicMock, call, patch


MOCK_CONFIG = {
    "personal_calendar_id": "personal@example.com",
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "baseline_event_id": "baseline-id",
    "baseline_event_title": "Daily Standup Alarm",
    "baseline_event_time": "09:25",
    "recurring_meetings": [],
    "meeting_type_prep": {},
    "locations": {},
    "client_overrides": {},
}

MOCK_RESULT = {
    "first_meeting_name": "AERSS Standup",
    "first_meeting_time": MagicMock(),
    "prep_minutes": 5,
    "alarm_time": MagicMock(),
    "is_baseline": False,
    "all_meetings": [],
    "unknown_blocks": [],
}

MOCK_POPUP_RESPONSE = {
    "confirmed": True,
    "alarm_time": MagicMock(),
    "skipped": False,
    "classifications": [],
}


class TestRunNightlySync(unittest.TestCase):

    def setUp(self):
        # Reset lock between tests
        import sync_job
        if sync_job._SYNC_LOCK.locked():
            sync_job._SYNC_LOCK.release()

    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value=MOCK_POPUP_RESPONSE)
    @patch("sync_job.compute_alarm", return_value=MOCK_RESULT)
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_run_nightly_sync_calls_pipeline_in_order(
        self,
        mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write,
    ):
        sync_job.run_nightly_sync()

        mock_read.assert_called_once()
        mock_parse.assert_called_once_with("yaml")
        mock_msi.assert_called_once()
        mock_personal.assert_called_once()
        mock_compute.assert_called_once_with([], [], MOCK_CONFIG, debug=False)
        mock_popup.assert_called_once_with(MOCK_RESULT, MOCK_CONFIG)
        mock_write.assert_called_once_with(
            MOCK_POPUP_RESPONSE,
            MOCK_CONFIG,
            meeting_name=MOCK_RESULT["first_meeting_name"],
            prep_minutes=MOCK_RESULT["prep_minutes"],
        )

    def test_run_nightly_sync_no_concurrent_run(self):
        import sync_job
        # Manually acquire the lock to simulate an in-progress sync
        sync_job._SYNC_LOCK.acquire()
        try:
            with patch("sync_job.read_config") as mock_read:
                sync_job.run_nightly_sync()
                mock_read.assert_not_called()
        finally:
            sync_job._SYNC_LOCK.release()

    @patch("sync_job.rumps")
    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup")
    @patch("sync_job.compute_alarm")
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", side_effect=Exception("Drive unreachable"))
    def test_run_nightly_sync_surfaces_error_on_exception(
        self,
        mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write, mock_rumps,
    ):
        # Should NOT raise
        sync_job.run_nightly_sync()

        mock_rumps.notification.assert_called_once()
        args = mock_rumps.notification.call_args[0]
        self.assertEqual(args[0], "Phantom Calendar")
        self.assertIn("Drive unreachable", args[2])
        mock_write.assert_not_called()

    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value=MOCK_POPUP_RESPONSE)
    @patch("sync_job.compute_alarm", return_value=MOCK_RESULT)
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_run_calendar_write_called_with_meeting_name_and_prep(
        self,
        mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write,
    ):
        sync_job.run_nightly_sync()

        _, kwargs = mock_write.call_args
        self.assertEqual(kwargs["meeting_name"], "AERSS Standup")
        self.assertEqual(kwargs["prep_minutes"], 5)

    @patch("sync_job.rumps")
    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value=MOCK_POPUP_RESPONSE)
    @patch("sync_job.compute_alarm", return_value=MOCK_RESULT)
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_lock_released_after_successful_run(
        self,
        mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write, mock_rumps,
    ):
        sync_job.run_nightly_sync()
        # Lock must be released so a second call can proceed
        self.assertFalse(sync_job._SYNC_LOCK.locked())

    @patch("sync_job.rumps")
    @patch("sync_job.read_config", side_effect=Exception("fail"))
    def test_lock_released_after_error(self, mock_read, mock_rumps):
        sync_job.run_nightly_sync()
        self.assertFalse(sync_job._SYNC_LOCK.locked())


class TestPromptUnknownLocations(unittest.TestCase):
    """Tests for _prompt_unknown_locations (AC 2.4–2.11)."""

    BASE_CONFIG = {
        "locations": {"Home": 0},
        "meeting_type_prep": {},
    }

    def _make_entry(self, title, start_iso, location):
        return {"title": title, "start_time": start_iso, "location": location}

    @patch("sync_job._osascript", return_value=("45", 0))
    def test_non_zero_integer_included_in_result(self, mock_osa):
        """AC 2.4 — non-zero integer input is captured."""
        entry = self._make_entry("Doctor", "2026-05-17T09:00:00", "200 N Nelson Dr")
        result, _ = sync_job._prompt_unknown_locations([entry], self.BASE_CONFIG, None)
        self.assertEqual(result, {"200 N Nelson Dr": 45})

    @patch("sync_job._osascript", return_value=("0", 0))
    def test_zero_input_excluded(self, mock_osa):
        """AC 2.10 — zero input yields empty dict."""
        entry = self._make_entry("Doctor", "2026-05-17T09:00:00", "200 N Nelson Dr")
        result, _ = sync_job._prompt_unknown_locations([entry], self.BASE_CONFIG, None)
        self.assertEqual(result, {})

    @patch("sync_job._osascript", return_value=("", 0))
    def test_blank_input_excluded(self, mock_osa):
        """AC 2.10 — blank input yields empty dict."""
        entry = self._make_entry("Doctor", "2026-05-17T09:00:00", "200 N Nelson Dr")
        result, _ = sync_job._prompt_unknown_locations([entry], self.BASE_CONFIG, None)
        self.assertEqual(result, {})

    @patch("sync_job._osascript", return_value=("abc", 0))
    def test_non_integer_input_excluded(self, mock_osa):
        """AC 2.4 — non-integer input yields empty dict."""
        entry = self._make_entry("Doctor", "2026-05-17T09:00:00", "200 N Nelson Dr")
        result, _ = sync_job._prompt_unknown_locations([entry], self.BASE_CONFIG, None)
        self.assertEqual(result, {})

    @patch("sync_job._osascript", return_value=("30", 1))
    def test_osascript_failure_treated_as_zero(self, mock_osa):
        """AC 2.11 — rc != 0 treated as input=0, no crash, no write."""
        entry = self._make_entry("Doctor", "2026-05-17T09:00:00", "200 N Nelson Dr")
        result, alarm = sync_job._prompt_unknown_locations([entry], self.BASE_CONFIG, None)
        self.assertEqual(result, {})
        self.assertIsNone(alarm)

    @patch("sync_job._osascript", return_value=("30", 0))
    def test_two_events_same_location_one_dialog(self, mock_osa):
        """AC 2.2 — events sharing the same location produce one dialog call."""
        entries = [
            self._make_entry("E1", "2026-05-17T09:00:00", "Office A"),
            self._make_entry("E2", "2026-05-17T14:00:00", "Office A"),
        ]
        result, _ = sync_job._prompt_unknown_locations(entries, self.BASE_CONFIG, None)
        # Only one osascript call for the shared location
        mock_osa.assert_called_once()
        self.assertEqual(result, {"Office A": 30})

    @patch("sync_job._osascript", side_effect=[("30", 0), ("45", 0)])
    def test_two_different_locations_two_dialogs(self, mock_osa):
        """AC 2.2 — two distinct locations produce two dialog calls."""
        entries = [
            self._make_entry("E1", "2026-05-17T09:00:00", "Office A"),
            self._make_entry("E2", "2026-05-17T14:00:00", "Office B"),
        ]
        result, _ = sync_job._prompt_unknown_locations(entries, self.BASE_CONFIG, None)
        self.assertEqual(mock_osa.call_count, 2)
        self.assertEqual(result, {"Office A": 30, "Office B": 45})

    @patch("sync_job._osascript", return_value=("30", 0))
    def test_alarm_recalculated_when_event_is_earlier(self, mock_osa):
        """AC 2.3 — alarm is pushed earlier when travel minutes apply."""
        from datetime import datetime, timedelta
        event_start = datetime(2026, 5, 17, 8, 0, 0)
        current_alarm = datetime(2026, 5, 17, 9, 0, 0)
        entry = self._make_entry("Early Appt", event_start.isoformat(), "Clinic")
        _, new_alarm = sync_job._prompt_unknown_locations(
            [entry], self.BASE_CONFIG, current_alarm
        )
        expected = event_start - timedelta(minutes=30)
        self.assertEqual(new_alarm, expected)

    @patch("sync_job._osascript", return_value=("5", 0))
    def test_alarm_unchanged_when_event_is_later(self, mock_osa):
        """AC 2.3 — alarm not moved later if event start minus travel > current alarm."""
        from datetime import datetime
        early_alarm = datetime(2026, 5, 17, 7, 0, 0)
        event_start = datetime(2026, 5, 17, 14, 0, 0)  # far later
        entry = self._make_entry("Late Appt", event_start.isoformat(), "Clinic")
        _, new_alarm = sync_job._prompt_unknown_locations(
            [entry], self.BASE_CONFIG, early_alarm
        )
        self.assertEqual(new_alarm, early_alarm)

    def test_empty_list_returns_empty_dict_and_unchanged_alarm(self):
        """AC 2.9 — empty unknown_locs list returns ({}, unchanged alarm)."""
        from datetime import datetime
        alarm = datetime(2026, 5, 17, 8, 0, 0)
        result, returned_alarm = sync_job._prompt_unknown_locations([], self.BASE_CONFIG, alarm)
        self.assertEqual(result, {})
        self.assertEqual(returned_alarm, alarm)


class TestShowPopupLocationTravelMinutes(unittest.TestCase):
    """Tests that _show_popup always returns location_travel_minutes key."""

    @patch("sync_job._osascript", return_value=("", 0))
    def test_no_meetings_returns_location_travel_minutes_key(self, mock_osa):
        """AC 2.12 — no-meetings path returns location_travel_minutes: {}."""
        result_dict = {"first_meeting_name": None}
        response = sync_job._show_popup(result_dict)
        self.assertIn("location_travel_minutes", response)
        self.assertEqual(response["location_travel_minutes"], {})

    @patch("sync_job._osascript", return_value=("", 1))
    def test_baseline_returns_location_travel_minutes_key(self, mock_osa):
        """AC 2.12 — baseline path returns location_travel_minutes."""
        from unittest.mock import MagicMock
        result_dict = {
            "first_meeting_name": "Standup",
            "first_meeting_time": MagicMock(),
            "alarm_time": MagicMock(),
            "prep_minutes": 5,
            "is_baseline": True,
            "unknown_blocks": [],
            "unknown_personal_locations": [],
        }
        response = sync_job._show_popup(result_dict, {})
        self.assertIn("location_travel_minutes", response)

    @patch("sync_job._osascript", return_value=("Skip||09:00", 0))
    def test_skipped_returns_location_travel_minutes_key(self, mock_osa):
        """AC 2.12 — skipped/cancelled path returns location_travel_minutes."""
        from unittest.mock import MagicMock
        result_dict = {
            "first_meeting_name": "Meeting",
            "first_meeting_time": MagicMock(),
            "alarm_time": MagicMock(strftime=MagicMock(return_value="09:00")),
            "prep_minutes": 5,
            "is_baseline": False,
            "unknown_blocks": [],
            "unknown_personal_locations": [],
        }
        response = sync_job._show_popup(result_dict, {})
        self.assertIn("location_travel_minutes", response)

    @patch("sync_job._prompt_unknown_locations", return_value=({"Clinic": 30}, MagicMock()))
    @patch("sync_job._osascript", return_value=("Write to Calendar||09:00", 0))
    def test_unknown_locs_prompt_called_and_merged(self, mock_osa, mock_prompt):
        """AC 2.1 & 2.5 — _prompt_unknown_locations called; result merged into response."""
        from unittest.mock import MagicMock
        alarm_mock = MagicMock()
        alarm_mock.strftime.return_value = "09:00"
        alarm_mock.replace.return_value = alarm_mock
        result_dict = {
            "first_meeting_name": "Doctor Visit",
            "first_meeting_time": MagicMock(strftime=MagicMock(return_value="10:00")),
            "alarm_time": alarm_mock,
            "prep_minutes": 30,
            "is_baseline": False,
            "unknown_blocks": [],
            "unknown_personal_locations": [
                {"title": "Doctor", "start_time": "2026-05-17T09:00:00", "location": "Clinic"}
            ],
        }
        response = sync_job._show_popup(result_dict, {"locations": {}})
        mock_prompt.assert_called_once()
        self.assertEqual(response["location_travel_minutes"], {"Clinic": 30})

    @patch("sync_job._prompt_unknown_locations")
    @patch("sync_job._osascript", return_value=("", 0))
    def test_prompt_not_called_for_empty_unknown_locs(self, mock_osa, mock_prompt):
        """AC 2.9 — _prompt_unknown_locations not called when list is empty."""
        result_dict = {
            "first_meeting_name": None,
            "unknown_personal_locations": [],
        }
        sync_job._show_popup(result_dict, {})
        mock_prompt.assert_not_called()


class TestAppendLocations(unittest.TestCase):
    """Tests for drive_config.append_locations (AC 2.6, 2.7)."""

    def setUp(self):
        import drive_config
        self.drive_config = drive_config

    @patch("drive_config.write_config")
    def test_new_locations_written_to_drive(self, mock_write):
        """AC 2.7 — new locations are serialised and written to Drive."""
        import yaml
        config = {
            "personal_calendar_id": "p@ex.com",
            "msi_calendar_id": "m@ex.com",
            "daily_run_time": "21:00",
            "timezone": "America/New_York",
            "default_prep_minutes": 30,
            "baseline_event_id": "",
            "baseline_event_title": "",
            "baseline_event_time": "09:25",
            "recurring_meetings": [],
            "meeting_type_prep": {},
            "locations": {"Home": 0},
            "client_overrides": {},
        }
        self.drive_config.append_locations({"Clinic": 45}, config)
        mock_write.assert_called_once()
        written_yaml = mock_write.call_args[0][0]
        parsed = yaml.safe_load(written_yaml)
        self.assertEqual(parsed["locations"]["Clinic"], 45)
        self.assertEqual(parsed["locations"]["Home"], 0)

    @patch("drive_config.write_config")
    def test_existing_location_not_overwritten(self, mock_write):
        """AC 2.7 — existing locations are NOT overwritten by new entries."""
        import yaml
        config = {
            "personal_calendar_id": "p@ex.com",
            "msi_calendar_id": "m@ex.com",
            "daily_run_time": "21:00",
            "timezone": "America/New_York",
            "default_prep_minutes": 30,
            "baseline_event_id": "",
            "baseline_event_title": "",
            "baseline_event_time": "09:25",
            "recurring_meetings": [],
            "meeting_type_prep": {},
            "locations": {"Home": 0, "Clinic": 20},
            "client_overrides": {},
        }
        # Attempt to overwrite Clinic with 45 — should remain 20
        self.drive_config.append_locations({"Clinic": 45}, config)
        mock_write.assert_called_once()
        written_yaml = mock_write.call_args[0][0]
        parsed = yaml.safe_load(written_yaml)
        self.assertEqual(parsed["locations"]["Clinic"], 20)


class TestRunNightlySyncWritesLocations(unittest.TestCase):
    """AC 2.6 — run_nightly_sync calls append_locations when location_travel_minutes non-empty."""

    def setUp(self):
        import sync_job
        if sync_job._SYNC_LOCK.locked():
            sync_job._SYNC_LOCK.release()

    @patch("sync_job.append_locations")
    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value={
        "confirmed": True,
        "alarm_time": MagicMock(),
        "skipped": False,
        "classifications": [],
        "location_travel_minutes": {"Clinic": 45},
    })
    @patch("sync_job.compute_alarm", return_value={**MOCK_RESULT, "unknown_personal_locations": []})
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_append_locations_called_when_non_empty(
        self, mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write, mock_append_locs,
    ):
        import sync_job
        sync_job.run_nightly_sync()
        mock_append_locs.assert_called_once_with({"Clinic": 45}, MOCK_CONFIG)

    @patch("sync_job.append_locations")
    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value={
        "confirmed": True,
        "alarm_time": MagicMock(),
        "skipped": False,
        "classifications": [],
        "location_travel_minutes": {},
    })
    @patch("sync_job.compute_alarm", return_value={**MOCK_RESULT, "unknown_personal_locations": []})
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_append_locations_not_called_when_empty(
        self, mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write, mock_append_locs,
    ):
        import sync_job
        sync_job.run_nightly_sync()
        mock_append_locs.assert_not_called()

    @patch("sync_job.append_locations", side_effect=Exception("Drive error"))
    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value={
        "confirmed": True,
        "alarm_time": MagicMock(),
        "skipped": False,
        "classifications": [],
        "location_travel_minutes": {"Clinic": 45},
    })
    @patch("sync_job.compute_alarm", return_value={**MOCK_RESULT, "unknown_personal_locations": []})
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=MOCK_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    def test_append_locations_failure_non_fatal(
        self, mock_read, mock_parse, mock_msi, mock_personal,
        mock_compute, mock_popup, mock_write, mock_append_locs,
    ):
        """AC 2.8 — append_locations failure does not raise or block calendar write."""
        import sync_job
        # Should not raise
        sync_job.run_nightly_sync()
        # Calendar write still happened
        mock_write.assert_called_once()


import sync_job  # noqa: E402


if __name__ == "__main__":
    unittest.main()
