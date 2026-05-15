"""Unit tests for NPC-0007: classification UI in _show_popup."""

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytz

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int) -> datetime:
    d = date.today() + timedelta(days=1)
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


BASE_CONFIG = {
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "recurring_meetings": [],
    "meeting_type_prep": {
        "Daily standup": 5,
        "Regular online meeting": 10,
        "In-person (local)": "travel+10",  # travel-time — should be excluded
        "Interview": 30,
    },
}

NORMAL_RESULT = {
    "first_meeting_name": "AERSS Standup",
    "first_meeting_time": _dt(9, 30),
    "prep_minutes": 5,
    "alarm_time": _dt(9, 25),
    "is_baseline": False,
    "all_meetings": [],
    "unknown_blocks": [],
}

BASELINE_RESULT = {**NORMAL_RESULT, "is_baseline": True}

NO_MEETINGS_RESULT = {
    "first_meeting_name": None,
    "first_meeting_time": None,
    "prep_minutes": 0,
    "alarm_time": None,
    "is_baseline": True,
    "all_meetings": [],
    "unknown_blocks": [],
}


class TestClassificationUI(unittest.TestCase):

    @patch("sync_job._osascript", return_value=("Write to Calendar||09:25", 0))
    def test_no_classification_dialog_when_no_unknown_blocks(self, mock_osc):
        result = sync_job._show_popup(NORMAL_RESULT, BASE_CONFIG)
        # Only one osascript call — the main dialog; no choose-from-list
        calls_text = [str(c) for c in mock_osc.call_args_list]
        self.assertFalse(any("choose from list" in t for t in calls_text))
        self.assertEqual(result["classifications"], [])

    @patch("sync_job._osascript")
    def test_classification_dialog_shown_for_each_unknown_block(self, mock_osc):
        unknown = [
            {"start": _dt(11, 0), "end": _dt(11, 30)},
            {"start": _dt(14, 0), "end": _dt(14, 30)},
        ]
        result_with_unknowns = {**NORMAL_RESULT, "unknown_blocks": unknown}
        # First two calls = classification dialogs, third = main dialog
        mock_osc.side_effect = [
            ("Skip (keep default)", 0),
            ("Skip (keep default)", 0),
            ("Write to Calendar||09:25", 0),
        ]
        sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        classify_calls = [
            c for c in mock_osc.call_args_list if "choose from list" in str(c)
        ]
        self.assertEqual(len(classify_calls), 2)

    @patch("sync_job._osascript")
    def test_selected_type_updates_alarm_time(self, mock_osc):
        unknown = [{"start": _dt(9, 30), "end": _dt(9, 45)}]
        result_with_unknowns = {
            **NORMAL_RESULT,
            "unknown_blocks": unknown,
            "alarm_time": _dt(9, 0),  # existing alarm, will be overridden
        }
        # User selects "Daily standup" (5 min prep) → alarm = 09:30 - 5 = 09:25
        mock_osc.side_effect = [
            ("Daily standup", 0),  # type selection
            ("Skip", 0),            # location selection (skip)
            ("Write to Calendar||09:25", 0),  # main dialog
        ]
        response = sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        # alarm_time in response should be 09:25 (block start 09:30 - 5 min)
        self.assertIsNotNone(response["alarm_time"])
        self.assertEqual(response["alarm_time"].hour, 9)
        self.assertEqual(response["alarm_time"].minute, 25)

    @patch("sync_job._osascript")
    def test_skipped_classification_not_in_response(self, mock_osc):
        unknown = [{"start": _dt(11, 0), "end": _dt(11, 30)}]
        result_with_unknowns = {**NORMAL_RESULT, "unknown_blocks": unknown}
        mock_osc.side_effect = [
            ("Skip (keep default)", 0),
            ("Write to Calendar||09:25", 0),
        ]
        response = sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        self.assertEqual(response["classifications"], [])

    @patch("sync_job._osascript")
    def test_non_skipped_classification_in_response(self, mock_osc):
        block_start = _dt(11, 0)
        unknown = [{"start": block_start, "end": _dt(11, 30)}]
        result_with_unknowns = {**NORMAL_RESULT, "unknown_blocks": unknown}
        mock_osc.side_effect = [
            ("Interview", 0),       # type selection
            ("Skip", 0),            # location selection (skip)
            ("Write to Calendar||09:25", 0),  # main dialog
        ]
        response = sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        self.assertEqual(len(response["classifications"]), 1)
        c = response["classifications"][0]
        self.assertEqual(c["meeting_type"], "Interview")
        self.assertEqual(c["prep_minutes"], 30)
        self.assertEqual(c["start_time"], block_start.isoformat())

    @patch("sync_job._osascript")
    def test_travel_time_types_excluded_from_list(self, mock_osc):
        unknown = [{"start": _dt(11, 0), "end": _dt(11, 30)}]
        result_with_unknowns = {**NORMAL_RESULT, "unknown_blocks": unknown}
        mock_osc.side_effect = [
            ("Skip (keep default)", 0),
            ("Write to Calendar||09:25", 0),
        ]
        sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        classify_call = str(mock_osc.call_args_list[0])
        self.assertNotIn("In-person (local)", classify_call)
        # But integer-prep types should be offered
        self.assertIn("Daily standup", classify_call)
        self.assertIn("Interview", classify_call)

    @patch("sync_job._osascript", return_value=("OK", 0))
    def test_baseline_result_skips_classification(self, mock_osc):
        unknown = [{"start": _dt(11, 0), "end": _dt(11, 30)}]
        result_with_unknowns = {**BASELINE_RESULT, "unknown_blocks": unknown}
        response = sync_job._show_popup(result_with_unknowns, BASE_CONFIG)
        # No choose-from-list call for baseline
        classify_calls = [
            c for c in mock_osc.call_args_list if "choose from list" in str(c)
        ]
        self.assertEqual(len(classify_calls), 0)
        self.assertEqual(response["classifications"], [])


import sync_job  # noqa: E402

if __name__ == "__main__":
    unittest.main()
