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
        mock_compute.assert_called_once_with([], [], MOCK_CONFIG)
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


import sync_job  # noqa: E402


if __name__ == "__main__":
    unittest.main()
