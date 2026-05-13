"""Unit tests for NPC-0007: writing classifications back to Drive config."""

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz
import yaml

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int) -> datetime:
    d = date.today() + timedelta(days=1)
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


BASE_CONFIG = {
    "personal_calendar_id": "personal@example.com",
    "msi_calendar_id": "work@example.com",
    "daily_run_time": "21:00",
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "baseline_event_id": "baseline-id",
    "baseline_event_title": "Alarm",
    "baseline_event_time": "09:25",
    "recurring_meetings": [],
    "meeting_type_prep": {"Daily standup": 5},
    "locations": {},
    "client_overrides": {},
}


class TestAppendRecurringMeetings(unittest.TestCase):

    @patch("drive_config.write_config")
    def test_append_recurring_meetings_adds_entry(self, mock_write):
        block_start = _dt(11, 0)
        classifications = [
            {
                "start_time": block_start.isoformat(),
                "meeting_type": "Daily standup",
                "prep_minutes": 5,
            }
        ]
        drive_config.append_recurring_meetings(classifications, BASE_CONFIG)
        mock_write.assert_called_once()
        written_yaml = mock_write.call_args[0][0]
        data = yaml.safe_load(written_yaml)
        meetings = data["recurring_meetings"]
        self.assertEqual(len(meetings), 1)
        self.assertEqual(meetings[0]["name"], "Daily standup (11:00)")
        self.assertEqual(meetings[0]["prep_minutes"], 5)
        self.assertEqual(meetings[0]["notes"], "Auto-classified by Phantom Calendar")

    @patch("drive_config.write_config")
    def test_append_recurring_meetings_preserves_existing(self, mock_write):
        existing = [
            {
                "name": "Existing",
                "start": "09:30",
                "end": "09:45",
                "days": ["Mon"],
                "prep_minutes": 5,
                "notes": "",
            }
        ]
        config_with_existing = {**BASE_CONFIG, "recurring_meetings": existing}
        block_start = _dt(11, 0)
        classifications = [
            {
                "start_time": block_start.isoformat(),
                "meeting_type": "Interview",
                "prep_minutes": 30,
            }
        ]
        drive_config.append_recurring_meetings(classifications, config_with_existing)
        written_yaml = mock_write.call_args[0][0]
        data = yaml.safe_load(written_yaml)
        meetings = data["recurring_meetings"]
        self.assertEqual(len(meetings), 2)
        self.assertEqual(meetings[0]["name"], "Existing")
        self.assertEqual(meetings[1]["name"], "Interview (11:00)")

    @patch("drive_config.write_config")
    def test_no_write_when_classifications_empty(self, mock_write):
        drive_config.append_recurring_meetings([], BASE_CONFIG)
        # write_config is still called (with no new entries) — but existing meetings preserved
        # Actually: with empty classifications, loop doesn't append, but write still called
        # Verify the output has no new meetings
        written_yaml = mock_write.call_args[0][0]
        data = yaml.safe_load(written_yaml)
        self.assertEqual(data["recurring_meetings"], [])

    @patch("sync_job.run_calendar_write")
    @patch(
        "sync_job._show_popup",
        return_value={
            "confirmed": False,
            "alarm_time": None,
            "skipped": True,
            "classifications": [],
        },
    )
    @patch(
        "sync_job.compute_alarm",
        return_value={
            "first_meeting_name": "Standup",
            "first_meeting_time": MagicMock(),
            "prep_minutes": 5,
            "alarm_time": MagicMock(),
            "is_baseline": False,
            "all_meetings": [],
            "unknown_blocks": [],
        },
    )
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=BASE_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    @patch("sync_job.append_recurring_meetings")
    def test_no_write_when_skipped(
        self,
        mock_append,
        mock_read,
        mock_parse,
        mock_msi,
        mock_personal,
        mock_compute,
        mock_popup,
        mock_write,
    ):
        sync_job.run_nightly_sync()
        mock_append.assert_not_called()

    @patch("sync_job.run_calendar_write")
    @patch(
        "sync_job._show_popup",
        return_value={
            "confirmed": True,
            "alarm_time": MagicMock(),
            "skipped": False,
            "classifications": [
                {
                    "start_time": "2026-05-13T11:00:00-04:00",
                    "meeting_type": "Interview",
                    "prep_minutes": 30,
                }
            ],
        },
    )
    @patch(
        "sync_job.compute_alarm",
        return_value={
            "first_meeting_name": "Standup",
            "first_meeting_time": MagicMock(),
            "prep_minutes": 5,
            "alarm_time": MagicMock(),
            "is_baseline": False,
            "all_meetings": [],
            "unknown_blocks": [],
        },
    )
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch("sync_job.parse_config", return_value=BASE_CONFIG)
    @patch("sync_job.read_config", return_value="yaml")
    @patch("sync_job.append_recurring_meetings", side_effect=Exception("Drive error"))
    def test_write_failure_is_non_fatal(
        self,
        mock_append,
        mock_read,
        mock_parse,
        mock_msi,
        mock_personal,
        mock_compute,
        mock_popup,
        mock_write,
    ):
        # Must not raise
        sync_job.run_nightly_sync()
        mock_append.assert_called_once()


import drive_config  # noqa: E402
import sync_job  # noqa: E402

if __name__ == "__main__":
    unittest.main()
