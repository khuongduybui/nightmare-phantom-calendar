"""Unit tests for calendar_writer.py — all Google API calls mocked."""

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytz

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int, day_offset: int = 1) -> datetime:
    """Build a tz-aware datetime for today+day_offset at hour:minute."""
    d = date.today() + timedelta(days=day_offset)
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


def _make_service():
    """Return a MagicMock that mimics the Google Calendar service chaining API."""
    service = MagicMock()
    # Default: execute() returns {}
    service.events.return_value.list.return_value.execute.return_value = {"items": []}
    service.events.return_value.instances.return_value.execute.return_value = {"items": []}
    service.events.return_value.insert.return_value.execute.return_value = {
        "id": "new-event-id",
        "summary": "⏰ Alarm — Test Meeting",
    }
    service.events.return_value.update.return_value.execute.return_value = {"id": "updated-id"}
    service.events.return_value.delete.return_value.execute.return_value = {}
    return service


CALENDAR_ID = "personal@example.com"
TZ_STR = "America/New_York"
BASELINE_ID = "baseline-event-id-123"


class TestCoreWriteOps(unittest.TestCase):

    def test_get_tomorrow_range_covers_next_day(self):
        tomorrow = date.today() + timedelta(days=1)
        start, end = calendar_writer.get_tomorrow_range(TZ_STR)
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        self.assertEqual(start_dt.date(), tomorrow)
        self.assertEqual(end_dt.date(), tomorrow)
        self.assertLess(start_dt, end_dt)

    def test_get_existing_alarm_returns_matching_events(self):
        service = _make_service()
        service.events.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "ev1", "summary": "⏰ Alarm — Standup"}]
        }
        result = calendar_writer.get_existing_alarm_for_tomorrow(service, CALENDAR_ID, TZ_STR)
        self.assertEqual(len(result), 1)
        # Verify ALARM_TAG was passed as q=
        call_kwargs = service.events.return_value.list.call_args[1]
        self.assertEqual(call_kwargs["q"], calendar_writer.ALARM_TAG)

    def test_get_existing_alarm_returns_empty_list_when_none(self):
        service = _make_service()
        result = calendar_writer.get_existing_alarm_for_tomorrow(service, CALENDAR_ID, TZ_STR)
        self.assertEqual(result, [])

    def test_delete_alarm_event_calls_api(self):
        service = _make_service()
        calendar_writer.delete_alarm_event(service, CALENDAR_ID, "event-123")
        service.events.return_value.delete.assert_called_once_with(
            calendarId=CALENDAR_ID, eventId="event-123"
        )
        service.events.return_value.delete.return_value.execute.assert_called_once()

    def test_write_alarm_event_correct_fields(self):
        service = _make_service()
        alarm_time = _dt(9, 25)
        calendar_writer.write_alarm_event(service, CALENDAR_ID, alarm_time, "AERSS Standup", TZ_STR, 5)
        inserted = service.events.return_value.insert.call_args[1]["body"]
        self.assertEqual(inserted["summary"], "⏰ Alarm — AERSS Standup")
        self.assertEqual(inserted["description"], calendar_writer.ALARM_TAG)
        self.assertEqual(inserted["start"]["timeZone"], TZ_STR)
        self.assertEqual(inserted["end"]["timeZone"], TZ_STR)

    def test_write_alarm_event_duration_equals_prep_minutes(self):
        service = _make_service()
        alarm_time = _dt(9, 0)
        prep = 30
        calendar_writer.write_alarm_event(service, CALENDAR_ID, alarm_time, "Meeting", TZ_STR, prep)
        inserted = service.events.return_value.insert.call_args[1]["body"]
        start_dt = datetime.fromisoformat(inserted["start"]["dateTime"])
        end_dt = datetime.fromisoformat(inserted["end"]["dateTime"])
        self.assertEqual(end_dt - start_dt, timedelta(minutes=prep))


class TestBaselineAndOrchestration(unittest.TestCase):

    def test_get_baseline_instance_returns_none_when_no_items(self):
        service = _make_service()
        result = calendar_writer.get_baseline_instance_for_tomorrow(
            service, CALENDAR_ID, BASELINE_ID, TZ_STR
        )
        self.assertIsNone(result)

    def test_get_baseline_instance_returns_first_item(self):
        service = _make_service()
        service.events.return_value.instances.return_value.execute.return_value = {
            "items": [{"id": "inst-001", "summary": "Daily Standup Alarm"}]
        }
        result = calendar_writer.get_baseline_instance_for_tomorrow(
            service, CALENDAR_ID, BASELINE_ID, TZ_STR
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "inst-001")

    @patch("calendar_writer.get_calendar_service")
    def test_run_skipped_makes_no_api_calls(self, mock_get_svc):
        calendar_writer.run_calendar_write(
            {"confirmed": False, "alarm_time": None, "skipped": True},
            {"personal_calendar_id": CALENDAR_ID, "timezone": TZ_STR},
            "Meeting",
            10,
        )
        mock_get_svc.assert_not_called()

    @patch("calendar_writer.get_calendar_service")
    def test_run_not_confirmed_makes_no_api_calls(self, mock_get_svc):
        calendar_writer.run_calendar_write(
            {"confirmed": False, "alarm_time": None, "skipped": False},
            {"personal_calendar_id": CALENDAR_ID, "timezone": TZ_STR},
            "Meeting",
            10,
        )
        mock_get_svc.assert_not_called()

    @patch("calendar_writer.get_calendar_service")
    def test_run_confirmed_deletes_existing_and_writes_new(self, mock_get_svc):
        service = _make_service()
        service.events.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "old-alarm", "summary": "⏰ Alarm — Old"}]
        }
        mock_get_svc.return_value = service
        calendar_writer.run_calendar_write(
            {"confirmed": True, "alarm_time": _dt(9, 25), "skipped": False},
            {"personal_calendar_id": CALENDAR_ID, "timezone": TZ_STR},
            "AERSS Standup",
            5,
        )
        service.events.return_value.delete.assert_called_once_with(
            calendarId=CALENDAR_ID, eventId="old-alarm"
        )
        service.events.return_value.insert.assert_called_once()

    @patch("calendar_writer.get_calendar_service")
    def test_run_confirmed_no_existing_alarm(self, mock_get_svc):
        service = _make_service()
        mock_get_svc.return_value = service
        calendar_writer.run_calendar_write(
            {"confirmed": True, "alarm_time": _dt(9, 25), "skipped": False},
            {"personal_calendar_id": CALENDAR_ID, "timezone": TZ_STR},
            "AERSS Standup",
            5,
        )
        service.events.return_value.delete.assert_not_called()
        service.events.return_value.insert.assert_called_once()

    @patch("calendar_writer.get_calendar_service")
    def test_run_overrides_baseline_occurrence_when_present(self, mock_get_svc):
        service = _make_service()
        service.events.return_value.instances.return_value.execute.return_value = {
            "items": [{"id": "inst-001", "summary": "Daily Standup Alarm"}]
        }
        mock_get_svc.return_value = service
        calendar_writer.run_calendar_write(
            {"confirmed": True, "alarm_time": _dt(9, 25), "skipped": False},
            {
                "personal_calendar_id": CALENDAR_ID,
                "timezone": TZ_STR,
                "baseline_event_id": BASELINE_ID,
            },
            "AERSS Standup",
            5,
        )
        service.events.return_value.update.assert_called_once_with(
            calendarId=CALENDAR_ID,
            eventId="inst-001",
            body=unittest.mock.ANY,
        )

    @patch("calendar_writer.get_calendar_service")
    def test_run_skips_baseline_override_when_no_instance(self, mock_get_svc):
        service = _make_service()
        mock_get_svc.return_value = service
        calendar_writer.run_calendar_write(
            {"confirmed": True, "alarm_time": _dt(9, 25), "skipped": False},
            {
                "personal_calendar_id": CALENDAR_ID,
                "timezone": TZ_STR,
                "baseline_event_id": BASELINE_ID,
            },
            "AERSS Standup",
            5,
        )
        service.events.return_value.update.assert_not_called()

    @patch("calendar_writer.get_calendar_service")
    def test_run_surfaces_write_error(self, mock_get_svc):
        service = _make_service()
        service.events.return_value.insert.return_value.execute.side_effect = Exception("API error")
        mock_get_svc.return_value = service
        with self.assertRaises(Exception) as ctx:
            calendar_writer.run_calendar_write(
                {"confirmed": True, "alarm_time": _dt(9, 25), "skipped": False},
                {"personal_calendar_id": CALENDAR_ID, "timezone": TZ_STR},
                "AERSS Standup",
                5,
            )
        self.assertIn("API error", str(ctx.exception))


import calendar_writer  # noqa: E402


if __name__ == "__main__":
    unittest.main()
