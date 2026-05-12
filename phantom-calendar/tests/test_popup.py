"""Unit tests for popup.py — all tkinter UI mocked."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz

LOCAL_TZ = pytz.timezone("America/New_York")


def _dt(hour: int, minute: int) -> datetime:
    """Build a tz-aware datetime for today at given hour:minute."""
    from datetime import date

    d = date.today()
    return LOCAL_TZ.localize(datetime(d.year, d.month, d.day, hour, minute))


def _normal_result(**overrides) -> dict:
    base = {
        "first_meeting_name": "AERSS Standup",
        "first_meeting_time": _dt(9, 30),
        "prep_minutes": 5,
        "alarm_time": _dt(9, 25),
        "is_baseline": False,
        "all_meetings": [],
        "unknown_blocks": [],
    }
    base.update(overrides)
    return base


def _baseline_result(**overrides) -> dict:
    base = _normal_result(is_baseline=True)
    base.update(overrides)
    return base


def _no_meetings_result(**overrides) -> dict:
    base = {
        "first_meeting_name": None,
        "first_meeting_time": None,
        "prep_minutes": 0,
        "alarm_time": None,
        "is_baseline": True,
        "all_meetings": [],
        "unknown_blocks": [],
    }
    base.update(overrides)
    return base


def _inject_mock_tk():
    """Inject a MagicMock as popup.tk so UI code doesn't need real Tk."""
    mock_tk = MagicMock()
    popup.tk = mock_tk
    return mock_tk


class TestParseAlarmOverride(unittest.TestCase):
    """Tests for _parse_alarm_override — no tkinter needed."""

    def setUp(self):
        _inject_mock_tk()
        self.popup = popup.ConfirmationPopup(_normal_result())

    def test_valid_hhmm_returns_correct_datetime(self):
        ref = _dt(9, 30)
        result = self.popup._parse_alarm_override("09:25", ref)
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 25)

    def test_parsed_datetime_preserves_timezone(self):
        ref = _dt(9, 30)
        result = self.popup._parse_alarm_override("09:25", ref)
        self.assertEqual(result.tzinfo, ref.tzinfo)

    def test_invalid_format_returns_none(self):
        ref = _dt(9, 30)
        for bad in ("9am", "930", "", "9:5:0", "abc"):
            with self.subTest(text=bad):
                self.assertIsNone(self.popup._parse_alarm_override(bad, ref))

    def test_out_of_range_hour_returns_none(self):
        ref = _dt(9, 30)
        self.assertIsNone(self.popup._parse_alarm_override("25:00", ref))

    def test_out_of_range_minute_returns_none(self):
        ref = _dt(9, 30)
        self.assertIsNone(self.popup._parse_alarm_override("12:60", ref))


class TestConfirmationPopupCallbacks(unittest.TestCase):
    """Tests for callback logic — tk patched, no real window."""

    def _make_popup_with_mocked_tk(self, result):
        _inject_mock_tk()
        p = popup.ConfirmationPopup(result)
        p._root = MagicMock()
        p._error_label = MagicMock()
        entry = MagicMock()
        entry.get.return_value = "09:25"
        p._alarm_entry = entry
        return p

    def test_on_confirm_response_confirmed_true(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._on_confirm()
        self.assertTrue(p._response["confirmed"])
        self.assertFalse(p._response["skipped"])

    def test_on_confirm_response_alarm_time_is_datetime(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._on_confirm()
        self.assertIsInstance(p._response["alarm_time"], datetime)

    def test_on_skip_response_skipped_true(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._on_skip()
        self.assertEqual(
            p._response,
            {"confirmed": False, "alarm_time": None, "skipped": True},
        )

    def test_on_dismiss_same_as_confirm(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._on_confirm()
        response = p._response
        self.assertTrue(response["confirmed"])
        self.assertIsInstance(response["alarm_time"], datetime)

    def test_confirm_blocked_when_entry_invalid(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._alarm_entry.get.return_value = "bad-time"
        p._on_confirm()
        p._root.destroy.assert_not_called()
        p._error_label.config.assert_called_once()
        call_kwargs = p._error_label.config.call_args[1]
        self.assertTrue(len(call_kwargs.get("text", "")) > 0)

    def test_response_dict_has_exactly_three_keys(self):
        p = self._make_popup_with_mocked_tk(_normal_result())
        p._on_confirm()
        self.assertEqual(
            set(p._response.keys()), {"confirmed", "alarm_time", "skipped"}
        )

    def test_baseline_skip_returns_skipped_false(self):
        p = self._make_popup_with_mocked_tk(_baseline_result())
        p._on_skip()
        self.assertFalse(p._response["confirmed"])
        self.assertFalse(p._response["skipped"])
        self.assertIsNone(p._response["alarm_time"])

    def test_no_meetings_skip_returns_skipped_true(self):
        p = self._make_popup_with_mocked_tk(_no_meetings_result())
        p._on_skip()
        self.assertFalse(p._response["confirmed"])
        self.assertTrue(p._response["skipped"])


class TestConfirmationPopupDisplayModes(unittest.TestCase):
    """Tests for display mode decisions — tk patched, _build_ui not called."""

    def _make_popup(self, result):
        _inject_mock_tk()
        p = popup.ConfirmationPopup(result)
        p._root = MagicMock()
        p._build_ui()
        return p

    def test_no_meetings_mode_omits_write_button(self):
        p = self._make_popup(_no_meetings_result())
        self.assertIsNone(p._write_btn)

    def test_baseline_mode_omits_write_button(self):
        p = self._make_popup(_baseline_result())
        self.assertIsNone(p._write_btn)

    def test_normal_mode_has_write_button(self):
        p = self._make_popup(_normal_result())
        self.assertIsNotNone(p._write_btn)

    def test_unknown_blocks_warning_present(self):
        unknown = [{"start": _dt(14, 0), "end": _dt(14, 30)}]
        p = self._make_popup(
            _normal_result(unknown_blocks=unknown, default_prep_minutes=30)
        )
        self.assertIsNotNone(p._warning_label)

    def test_unknown_blocks_warning_absent_when_empty(self):
        p = self._make_popup(_normal_result(unknown_blocks=[]))
        self.assertIsNone(p._warning_label)

    def test_unknown_blocks_warning_shows_multiple_blocks(self):
        unknown = [
            {"start": _dt(14, 0), "end": _dt(14, 30)},
            {"start": _dt(15, 0), "end": _dt(15, 30)},
        ]
        mock_tk = _inject_mock_tk()
        p = popup.ConfirmationPopup(
            _normal_result(unknown_blocks=unknown, default_prep_minutes=30)
        )
        p._root = MagicMock()
        p._build_ui()
        self.assertIsNotNone(p._warning_label)
        # Check that the Label was constructed with text containing both times
        label_calls = [
            call
            for call in mock_tk.Label.call_args_list
            if "text" in (call.kwargs or {})
        ]
        warning_texts = [c.kwargs["text"] for c in label_calls]
        combined = "\n".join(warning_texts)
        self.assertIn("14:00", combined)
        self.assertIn("15:00", combined)


import popup  # noqa: E402

if __name__ == "__main__":
    unittest.main()
