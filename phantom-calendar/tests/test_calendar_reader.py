"""Unit tests for calendar_reader.py."""

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz


def _make_event(summary, start_dt, end_dt=None, all_day=False):
    """Helper to build a mock Google Calendar API event dict."""
    if all_day:
        return {
            "summary": summary,
            "start": {"date": start_dt.strftime("%Y-%m-%d")},
            "end": {"date": start_dt.strftime("%Y-%m-%d")},
        }
    return {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()} if end_dt else {},
    }


class TestGetTomorrowRange(unittest.TestCase):

    def test_get_tomorrow_range_covers_next_day(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        start_iso, end_iso = calendar_reader.get_tomorrow_range()
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        self.assertEqual(start.date(), tomorrow)
        self.assertEqual(end.date(), tomorrow)
        self.assertLess(start, end)


class TestGetMsiTimeBlocks(unittest.TestCase):

    @patch("calendar_reader.get_calendar_service")
    def test_get_msi_time_blocks_returns_start_end_only(self, mock_svc):
        tz = pytz.timezone("America/New_York")
        tomorrow = date.today() + timedelta(days=1)
        start_dt = tz.localize(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 30)
        )
        end_dt = tz.localize(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 45)
        )
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": [_make_event("Secret Meeting", start_dt, end_dt)]
        }
        result = calendar_reader.get_msi_time_blocks()
        self.assertEqual(len(result), 1)
        self.assertIn("start", result[0])
        self.assertIn("end", result[0])
        self.assertNotIn("title", result[0])
        self.assertNotIn("summary", result[0])

    @patch("calendar_reader.get_calendar_service")
    def test_get_msi_time_blocks_skips_all_day_events(self, mock_svc):
        tomorrow = date.today() + timedelta(days=1)
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": [_make_event("All Day", tomorrow, all_day=True)]
        }
        result = calendar_reader.get_msi_time_blocks()
        self.assertEqual(result, [])

    @patch("calendar_reader.get_calendar_service")
    def test_get_msi_time_blocks_empty_list(self, mock_svc):
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        result = calendar_reader.get_msi_time_blocks()
        self.assertEqual(result, [])

    @patch("calendar_reader.get_calendar_service")
    def test_get_msi_time_blocks_sorted_ascending(self, mock_svc):
        tz = pytz.timezone("America/New_York")
        tomorrow = date.today() + timedelta(days=1)
        early = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 0))
        late = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 14, 0))
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": [
                _make_event("Late", late, late + timedelta(hours=1)),
                _make_event("Early", early, early + timedelta(minutes=30)),
            ]
        }
        result = calendar_reader.get_msi_time_blocks()
        self.assertLess(result[0]["start"], result[1]["start"])


class TestGetPersonalEvents(unittest.TestCase):

    @patch("calendar_reader.get_calendar_service")
    def test_get_personal_events_includes_title(self, mock_svc):
        tz = pytz.timezone("America/New_York")
        tomorrow = date.today() + timedelta(days=1)
        start_dt = tz.localize(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0)
        )
        end_dt = tz.localize(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 30)
        )
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": [_make_event("Stand-up", start_dt, end_dt)]
        }
        result = calendar_reader.get_personal_events()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Stand-up")
        self.assertIsInstance(result[0]["start"], datetime)

    @patch("calendar_reader.get_calendar_service")
    def test_get_personal_events_empty_list(self, mock_svc):
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        result = calendar_reader.get_personal_events()
        self.assertEqual(result, [])

    @patch("calendar_reader.get_calendar_service")
    def test_get_personal_events_skips_all_day(self, mock_svc):
        tomorrow = date.today() + timedelta(days=1)
        mock_svc.return_value.events.return_value.list.return_value.execute.return_value = {
            "items": [_make_event("Holiday", tomorrow, all_day=True)]
        }
        result = calendar_reader.get_personal_events()
        self.assertEqual(result, [])


import calendar_reader  # noqa: E402

if __name__ == "__main__":
    unittest.main()
