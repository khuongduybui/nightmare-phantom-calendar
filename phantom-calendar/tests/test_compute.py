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

    def test_compute_alarm_result_has_all_8_keys(self):
        result = compute.compute_alarm([], [], BASE_CONFIG)
        expected_keys = {
            "first_meeting_name",
            "first_meeting_time",
            "prep_minutes",
            "alarm_time",
            "is_baseline",
            "all_meetings",
            "unknown_blocks",
            "unknown_personal_locations",
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


CONFIG_WITH_LOCATIONS = {
    **BASE_CONFIG,
    "locations": {
        "Home": 0,
        "Office": 25,
    },
}


class TestUnknownPersonalLocations(unittest.TestCase):

    def test_unknown_location_detected(self):
        # AC 1.1 — non-empty, non-Home, not in locations → detected
        personal = [
            {
                "title": "Doctor",
                "start": _dt(10, 0),
                "end": _dt(10, 30),
                "location": "200 N Nelson Dr, Fountain Inn SC",
            }
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(len(result["unknown_personal_locations"]), 1)
        entry = result["unknown_personal_locations"][0]
        self.assertEqual(entry["title"], "Doctor")
        self.assertEqual(entry["location"], "200 N Nelson Dr, Fountain Inn SC")
        self.assertEqual(entry["start_time"], _dt(10, 0).isoformat())

    def test_known_location_excluded(self):
        # AC 1.2 — location IS in config["locations"] → not surfaced
        personal = [
            {
                "title": "Office meeting",
                "start": _dt(10, 0),
                "end": _dt(10, 30),
                "location": "Office",
            }
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(result["unknown_personal_locations"], [])

    def test_none_location_excluded(self):
        # AC 1.3 — None location → not surfaced
        personal = [
            {"title": "Call", "start": _dt(10, 0), "end": _dt(10, 30), "location": None}
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(result["unknown_personal_locations"], [])

    def test_empty_string_location_excluded(self):
        # AC 1.3 — empty string location → not surfaced
        personal = [
            {"title": "Call", "start": _dt(10, 0), "end": _dt(10, 30), "location": ""}
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(result["unknown_personal_locations"], [])

    def test_home_location_excluded(self):
        # AC 1.4 — "Home" → not surfaced
        personal = [
            {
                "title": "WFH",
                "start": _dt(10, 0),
                "end": _dt(10, 30),
                "location": "Home",
            }
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(result["unknown_personal_locations"], [])

    def test_two_events_same_unknown_location_not_deduplicated(self):
        # AC 1.5 — two events, same unknown location → two entries
        personal = [
            {
                "title": "Lunch",
                "start": _dt(12, 0),
                "end": _dt(13, 0),
                "location": "Gym",
            },
            {
                "title": "Dinner",
                "start": _dt(18, 0),
                "end": _dt(19, 0),
                "location": "Gym",
            },
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(len(result["unknown_personal_locations"]), 2)
        titles = {e["title"] for e in result["unknown_personal_locations"]}
        self.assertEqual(titles, {"Lunch", "Dinner"})

    def test_unknown_personal_locations_always_present(self):
        # AC 1.7 — key always present even with no events
        result = compute.compute_alarm([], [], BASE_CONFIG)
        self.assertIn("unknown_personal_locations", result)
        self.assertEqual(result["unknown_personal_locations"], [])

    def test_alarm_events_not_surfaced_as_unknown_locations(self):
        # Alarm events are skipped entirely — should not appear in unknown_personal_locations
        personal = [
            {
                "title": "Daily Standup Alarm",
                "start": _dt(9, 25),
                "end": _dt(9, 30),
                "location": "Mystery Hall",
            }
        ]
        result = compute.compute_alarm([], personal, CONFIG_WITH_LOCATIONS)
        self.assertEqual(result["unknown_personal_locations"], [])


import compute  # noqa: E402


if __name__ == "__main__":
    unittest.main()
