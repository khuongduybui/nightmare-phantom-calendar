"""Unit tests for compute.py."""

import unittest
from datetime import datetime, timedelta

import pytz

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour, minute, day_offset=1):
    """Build a timezone-aware datetime for tomorrow at given hour:minute."""
    from datetime import date
    base = date.today() + timedelta(days=day_offset)
    naive = datetime(base.year, base.month, base.day, hour, minute)
    return LOCAL_TZ.localize(naive)


RECURRING_MEETINGS = [
    {
        "name": "AERSS Standup",
        "start": "09:30",
        "end": "09:45",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "prep_minutes": 5,
        "notes": "",
    },
    {
        "name": "Pod 8 Daily Sync",
        "start": "12:30",
        "end": "12:45",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "prep_minutes": 15,
        "notes": "",
    },
]

BASE_CONFIG = {
    "recurring_meetings": RECURRING_MEETINGS,
    "default_prep_minutes": 30,
    "baseline_event_title": "AERSS Standup",
    "baseline_event_time": "09:25",
}


class TestMatchBlockToMeeting(unittest.TestCase):

    def test_match_within_5_min_returns_meeting(self):
        # Block starts 4 minutes after AERSS Standup (09:34)
        block = {"start": _dt(9, 34), "end": _dt(9, 45)}
        result = compute.match_block_to_meeting(block, RECURRING_MEETINGS)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "AERSS Standup")

    def test_match_outside_tolerance_returns_none(self):
        # Block starts 6 minutes after AERSS Standup (09:36)
        block = {"start": _dt(9, 36), "end": _dt(9, 46)}
        result = compute.match_block_to_meeting(block, RECURRING_MEETINGS)
        self.assertIsNone(result)

    def test_match_exact_time_returns_meeting(self):
        block = {"start": _dt(12, 30), "end": _dt(12, 45)}
        result = compute.match_block_to_meeting(block, RECURRING_MEETINGS)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Pod 8 Daily Sync")

    def test_match_empty_meetings_returns_none(self):
        block = {"start": _dt(9, 30), "end": _dt(9, 45)}
        result = compute.match_block_to_meeting(block, [])
        self.assertIsNone(result)


class TestComputeAlarm(unittest.TestCase):

    def test_compute_alarm_known_block_uses_meeting_prep(self):
        msi_blocks = [{"start": _dt(9, 30), "end": _dt(9, 45)}]
        result = compute.compute_alarm(msi_blocks, [], BASE_CONFIG)
        self.assertEqual(result["first_meeting_name"], "AERSS Standup")
        self.assertEqual(result["prep_minutes"], 5)
        self.assertEqual(result["unknown_blocks"], [])
        expected_alarm = _dt(9, 25)
        self.assertEqual(result["alarm_time"], expected_alarm)

    def test_compute_alarm_unknown_block_uses_default_prep(self):
        # Block at 11:00 — no matching recurring meeting
        msi_blocks = [{"start": _dt(11, 0), "end": _dt(11, 30)}]
        result = compute.compute_alarm(msi_blocks, [], BASE_CONFIG)
        self.assertEqual(result["first_meeting_name"], "Unknown MSI meeting")
        self.assertEqual(result["prep_minutes"], 30)
        self.assertEqual(len(result["unknown_blocks"]), 1)

    def test_compute_alarm_excludes_alarm_events(self):
        personal = [
            {"title": "Standup Alarm", "start": _dt(9, 25), "end": _dt(9, 30)},
            {"title": "Team lunch", "start": _dt(12, 0), "end": _dt(13, 0)},
        ]
        result = compute.compute_alarm([], personal, BASE_CONFIG)
        self.assertEqual(result["first_meeting_name"], "Team lunch")

    def test_compute_alarm_picks_earliest(self):
        msi_blocks = [{"start": _dt(12, 30), "end": _dt(12, 45)}]
        personal = [{"title": "Early call", "start": _dt(8, 0), "end": _dt(8, 30)}]
        result = compute.compute_alarm(msi_blocks, personal, BASE_CONFIG)
        self.assertEqual(result["first_meeting_name"], "Early call")
        self.assertEqual(result["first_meeting_time"], _dt(8, 0))

    def test_compute_alarm_no_meetings(self):
        result = compute.compute_alarm([], [], BASE_CONFIG)
        self.assertIsNone(result["first_meeting_name"])
        self.assertIsNone(result["first_meeting_time"])
        self.assertEqual(result["prep_minutes"], 0)
        self.assertIsNone(result["alarm_time"])
        self.assertTrue(result["is_baseline"])
        self.assertEqual(result["all_meetings"], [])

    def test_compute_alarm_result_has_all_7_keys(self):
        result = compute.compute_alarm([], [], BASE_CONFIG)
        expected_keys = {
            "first_meeting_name", "first_meeting_time", "prep_minutes",
            "alarm_time", "is_baseline", "all_meetings", "unknown_blocks",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_compute_alarm_is_baseline_true_for_aerss_standup(self):
        msi_blocks = [{"start": _dt(9, 30), "end": _dt(9, 45)}]
        result = compute.compute_alarm(msi_blocks, [], BASE_CONFIG)
        self.assertTrue(result["is_baseline"])

    def test_compute_alarm_is_baseline_false_for_other_meeting(self):
        msi_blocks = [{"start": _dt(12, 30), "end": _dt(12, 45)}]
        result = compute.compute_alarm(msi_blocks, [], BASE_CONFIG)
        self.assertFalse(result["is_baseline"])


import compute  # noqa: E402


if __name__ == "__main__":
    unittest.main()
