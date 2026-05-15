"""Unit tests for preferences.py — osascript-based implementation."""

import unittest
from unittest.mock import patch


BASE_CONFIG = {
    "daily_run_time": "21:00",
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "personal_calendar_id": "personal@example.com",
    "msi_calendar_id": "work@example.com",
}


VALID = ["21:00", "America/New_York", "30", "personal@example.com", "work@example.com"]
UPDATED = ["20:00", "US/Pacific", "15", "new@example.com", "work2@example.com"]


class TestPreferencesWindow(unittest.TestCase):

    @patch("preferences._ask", return_value=None)
    def test_cancel_returns_none(self, _):
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())

    @patch("preferences._edit_locations", return_value={"Home": 0})
    @patch("preferences._ask")
    def test_save_returns_updated(self, mock_ask, _mock_locs):
        mock_ask.side_effect = UPDATED
        r = preferences.PreferencesWindow(BASE_CONFIG).show()
        self.assertEqual(r["daily_run_time"], "20:00")
        self.assertEqual(r["default_prep_minutes"], 15)

    @patch("preferences._osascript")
    @patch("preferences._ask")
    def test_bad_trigger_blocks_save(self, mock_ask, mock_osc):
        mock_ask.side_effect = ["25:00"] + VALID[1:]
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())
        mock_osc.assert_called()

    @patch("preferences._osascript")
    @patch("preferences._ask")
    def test_bad_trigger_format_blocks_save(self, mock_ask, mock_osc):
        mock_ask.side_effect = ["9pm"] + VALID[1:]
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())

    @patch("preferences._osascript")
    @patch("preferences._ask")
    def test_bad_prep_minutes_blocks_save(self, mock_ask, mock_osc):
        mock_ask.side_effect = VALID[:2] + ["abc"] + VALID[3:]
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())

    @patch("preferences._osascript")
    @patch("preferences._ask")
    def test_zero_prep_minutes_blocks_save(self, mock_ask, mock_osc):
        mock_ask.side_effect = VALID[:2] + ["0"] + VALID[3:]
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())

    @patch("preferences._ask")
    def test_cancel_midway_returns_none(self, mock_ask):
        mock_ask.side_effect = [VALID[0], VALID[1], None]
        self.assertIsNone(preferences.PreferencesWindow(BASE_CONFIG).show())


import preferences  # noqa: E402


if __name__ == "__main__":
    unittest.main()
