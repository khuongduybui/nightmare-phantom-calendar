"""Unit tests for apple_calendar.py."""

import json
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import apple_calendar


class TestIsAccessible(unittest.TestCase):

    @patch("apple_calendar.platform")
    def test_returns_false_on_non_macos(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        self.assertFalse(apple_calendar.is_accessible())
        # subprocess should not be called
        mock_platform.mac_ver.assert_not_called()

    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_false_when_macos_version_too_old(self, mock_platform, mock_shutil):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("13.6.1", ("", "", ""), "")
        self.assertFalse(apple_calendar.is_accessible())
        mock_shutil.which.assert_not_called()

    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_false_when_ical_guy_missing(self, mock_platform, mock_shutil):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("15.0", ("", "", ""), "")
        mock_shutil.which.return_value = None
        self.assertFalse(apple_calendar.is_accessible())

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_false_when_probe_fails(
        self, mock_platform, mock_shutil, mock_subprocess
    ):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("15.0", ("", "", ""), "")
        mock_shutil.which.return_value = "/usr/local/bin/ical-guy"
        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout="", stderr="denied"
        )
        self.assertFalse(apple_calendar.is_accessible())

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_false_when_probe_returns_invalid_json(
        self, mock_platform, mock_shutil, mock_subprocess
    ):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("14.4.1", ("", "", ""), "")
        mock_shutil.which.return_value = "/usr/local/bin/ical-guy"
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="not json")
        self.assertFalse(apple_calendar.is_accessible())

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_true_on_success(self, mock_platform, mock_shutil, mock_subprocess):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("15.0", ("", "", ""), "")
        mock_shutil.which.return_value = "/usr/local/bin/ical-guy"
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"id": "1", "title": "Work", "type": "calDAV"}]),
        )
        self.assertTrue(apple_calendar.is_accessible())

    @patch("apple_calendar.platform")
    def test_returns_false_when_mac_ver_empty(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("", ("", "", ""), "")
        self.assertFalse(apple_calendar.is_accessible())

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.shutil")
    @patch("apple_calendar.platform")
    def test_returns_false_on_subprocess_timeout(
        self, mock_platform, mock_shutil, mock_subprocess
    ):
        mock_platform.system.return_value = "Darwin"
        mock_platform.mac_ver.return_value = ("15.0", ("", "", ""), "")
        mock_shutil.which.return_value = "/usr/local/bin/ical-guy"
        mock_subprocess.run.side_effect = TimeoutError("timeout")
        self.assertFalse(apple_calendar.is_accessible())


SAMPLE_EVENTS_JSON = json.dumps(
    [
        {
            "id": "ev-1",
            "title": "Team Standup",
            "startDate": "2026-05-18T09:00:00-04:00",
            "endDate": "2026-05-18T09:30:00-04:00",
            "isAllDay": False,
            "location": "Room A",
            "notes": "Daily sync",
        },
        {
            "id": "ev-2",
            "title": "Lunch Break",
            "startDate": "2026-05-18T12:00:00-04:00",
            "endDate": "2026-05-18T13:00:00-04:00",
            "isAllDay": False,
            "location": None,
            "notes": None,
        },
        {
            "id": "ev-3",
            "title": "All Day Holiday",
            "startDate": "2026-05-18T00:00:00-04:00",
            "endDate": "2026-05-19T00:00:00-04:00",
            "isAllDay": True,
            "location": None,
            "notes": None,
        },
        {
            "id": "ev-4",
            "title": "Late Night (next day)",
            "startDate": "2026-05-19T00:30:00-04:00",
            "endDate": "2026-05-19T01:00:00-04:00",
            "isAllDay": False,
            "location": None,
            "notes": None,
        },
    ]
)


class TestGetTomorrowEvents(unittest.TestCase):

    @patch("apple_calendar.is_accessible", return_value=False)
    def test_raises_when_not_accessible(self, _mock):
        with self.assertRaises(RuntimeError) as ctx:
            apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertIn("not accessible", str(ctx.exception))

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_returns_timed_events_for_target_date(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["title"], "Team Standup")
        self.assertEqual(events[1]["title"], "Lunch Break")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_excludes_all_day_events(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        titles = [e["title"] for e in events]
        self.assertNotIn("All Day Holiday", titles)

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_excludes_events_from_other_dates(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        titles = [e["title"] for e in events]
        self.assertNotIn("Late Night (next day)", titles)

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_description_from_notes(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events[0]["description"], "Daily sync")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_description_empty_when_notes_null(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events[1]["description"], "")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_location_preserved(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events[0]["location"], "Room A")
        self.assertIsNone(events[1]["location"])

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_sorted_by_start_ascending(self, _mock_acc, mock_subprocess):
        reversed_json = json.dumps(
            [
                {
                    "id": "2",
                    "title": "Later",
                    "startDate": "2026-05-18T14:00:00-04:00",
                    "endDate": "2026-05-18T15:00:00-04:00",
                    "isAllDay": False,
                    "location": None,
                    "notes": None,
                },
                {
                    "id": "1",
                    "title": "Earlier",
                    "startDate": "2026-05-18T08:00:00-04:00",
                    "endDate": "2026-05-18T09:00:00-04:00",
                    "isAllDay": False,
                    "location": None,
                    "notes": None,
                },
            ]
        )
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=reversed_json, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events[0]["title"], "Earlier")
        self.assertEqual(events[1]["title"], "Later")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_raises_on_nonzero_exit(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout="", stderr="permission denied"
        )
        with self.assertRaises(RuntimeError) as ctx:
            apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertIn("permission denied", str(ctx.exception))

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_raises_on_unparseable_json(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="not json at all", stderr=""
        )
        with self.assertRaises(RuntimeError) as ctx:
            apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertIn("unparseable", str(ctx.exception))

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_exclude_calendars_passed_to_args(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="[]", stderr=""
        )
        apple_calendar.get_tomorrow_events(
            date(2026, 5, 18),
            exclude_calendars=["US Holidays", "Birthdays"],
        )
        call_args = mock_subprocess.run.call_args[0][0]
        self.assertIn("--exclude-calendars", call_args)
        idx = call_args.index("--exclude-calendars")
        self.assertEqual(call_args[idx + 1], "US Holidays,Birthdays")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_no_exclude_flag_when_none(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="[]", stderr=""
        )
        apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        call_args = mock_subprocess.run.call_args[0][0]
        self.assertNotIn("--exclude-calendars", call_args)

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_untitled_event_gets_default_title(self, _mock_acc, mock_subprocess):
        ev_json = json.dumps(
            [
                {
                    "id": "u1",
                    "title": None,
                    "startDate": "2026-05-18T10:00:00-04:00",
                    "endDate": "2026-05-18T11:00:00-04:00",
                    "isAllDay": False,
                    "location": None,
                    "notes": None,
                }
            ]
        )
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=ev_json, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events[0]["title"], "Untitled")

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_start_datetime_is_timezone_aware(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=SAMPLE_EVENTS_JSON, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertIsNotNone(events[0]["start"].tzinfo)

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_empty_events_returns_empty_list(self, _mock_acc, mock_subprocess):
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="[]", stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(events, [])

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_end_dt_falls_back_to_start_dt_when_end_date_absent(
        self, _mock_acc, mock_subprocess
    ):
        ev_json = json.dumps(
            [
                {
                    "id": "e1",
                    "title": "No End",
                    "startDate": "2026-05-18T10:00:00-04:00",
                    "endDate": "",
                    "isAllDay": False,
                    "location": None,
                    "notes": None,
                }
            ]
        )
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=ev_json, stderr=""
        )
        events = apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["end"], events[0]["start"])

    @patch("apple_calendar.subprocess")
    @patch("apple_calendar.is_accessible", return_value=True)
    def test_raises_runtime_error_on_malformed_start_date(
        self, _mock_acc, mock_subprocess
    ):
        ev_json = json.dumps(
            [
                {
                    "id": "bad1",
                    "title": "Bad Date",
                    "startDate": "not-a-date",
                    "endDate": "",
                    "isAllDay": False,
                    "location": None,
                    "notes": None,
                }
            ]
        )
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=ev_json, stderr=""
        )
        with self.assertRaises(RuntimeError) as ctx:
            apple_calendar.get_tomorrow_events(date(2026, 5, 18))
        self.assertIn("invalid startDate", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
