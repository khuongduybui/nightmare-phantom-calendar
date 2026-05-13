"""Unit tests for preferences.py — all tkinter mocked."""

import unittest
from unittest.mock import MagicMock, patch


BASE_CONFIG = {
    "daily_run_time": "21:00",
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "personal_calendar_id": "personal@example.com",
    "msi_calendar_id": "work@example.com",
}


def _inject_mock_tk():
    """Inject a MagicMock as preferences.tk so UI code doesn't need real Tk."""
    mock_tk = MagicMock()
    preferences.tk = mock_tk
    return mock_tk


def _make_prefs(config=None):
    _inject_mock_tk()
    return preferences.PreferencesWindow(config or BASE_CONFIG)


class TestPreferencesWindow(unittest.TestCase):

    def test_show_returns_none_on_cancel(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._on_cancel()
        self.assertIsNone(p._result)

    def test_show_returns_none_on_window_dismiss(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._on_cancel()  # WM_DELETE_WINDOW calls _on_cancel
        self.assertIsNone(p._result)

    def test_show_returns_updated_config_on_save(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._error_label = MagicMock()
        # Set up entries with valid values
        entries = {
            "daily_run_time": MagicMock(get=lambda: "20:00"),
            "timezone": MagicMock(get=lambda: "US/Pacific"),
            "default_prep_minutes": MagicMock(get=lambda: "15"),
            "personal_calendar_id": MagicMock(get=lambda: "new@example.com"),
            "msi_calendar_id": MagicMock(get=lambda: "work2@example.com"),
        }
        p._entries = entries
        p._on_save()
        self.assertIsNotNone(p._result)
        self.assertEqual(p._result["daily_run_time"], "20:00")
        self.assertEqual(p._result["default_prep_minutes"], 15)
        self.assertEqual(p._result["timezone"], "US/Pacific")

    def test_invalid_trigger_time_blocks_save(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._error_label = MagicMock()
        entries = {
            "daily_run_time": MagicMock(get=lambda: "25:00"),
            "timezone": MagicMock(get=lambda: "America/New_York"),
            "default_prep_minutes": MagicMock(get=lambda: "30"),
            "personal_calendar_id": MagicMock(get=lambda: "p@e.com"),
            "msi_calendar_id": MagicMock(get=lambda: "m@e.com"),
        }
        p._entries = entries
        p._on_save()
        p._root.destroy.assert_not_called()
        self.assertIsNone(p._result)

    def test_invalid_trigger_time_format_blocks_save(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._error_label = MagicMock()
        entries = {
            "daily_run_time": MagicMock(get=lambda: "9pm"),
            "timezone": MagicMock(get=lambda: "America/New_York"),
            "default_prep_minutes": MagicMock(get=lambda: "30"),
            "personal_calendar_id": MagicMock(get=lambda: "p@e.com"),
            "msi_calendar_id": MagicMock(get=lambda: "m@e.com"),
        }
        p._entries = entries
        p._on_save()
        p._root.destroy.assert_not_called()

    def test_invalid_prep_minutes_blocks_save(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._error_label = MagicMock()
        entries = {
            "daily_run_time": MagicMock(get=lambda: "21:00"),
            "timezone": MagicMock(get=lambda: "America/New_York"),
            "default_prep_minutes": MagicMock(get=lambda: "abc"),
            "personal_calendar_id": MagicMock(get=lambda: "p@e.com"),
            "msi_calendar_id": MagicMock(get=lambda: "m@e.com"),
        }
        p._entries = entries
        p._on_save()
        p._root.destroy.assert_not_called()
        self.assertIsNone(p._result)

    def test_zero_prep_minutes_blocks_save(self):
        p = _make_prefs()
        p._root = MagicMock()
        p._error_label = MagicMock()
        entries = {
            "daily_run_time": MagicMock(get=lambda: "21:00"),
            "timezone": MagicMock(get=lambda: "America/New_York"),
            "default_prep_minutes": MagicMock(get=lambda: "0"),
            "personal_calendar_id": MagicMock(get=lambda: "p@e.com"),
            "msi_calendar_id": MagicMock(get=lambda: "m@e.com"),
        }
        p._entries = entries
        p._on_save()
        self.assertIsNone(p._result)


import preferences  # noqa: E402


if __name__ == "__main__":
    unittest.main()
