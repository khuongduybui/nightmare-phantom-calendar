"""Unit tests for scheduler.py."""

import threading
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz


TZ_STR = "America/New_York"


class TestStartScheduler(unittest.TestCase):

    @patch("scheduler.CronTrigger")
    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_adds_cron_job(self, mock_scheduler_cls, mock_cron_cls):
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        scheduler.start_scheduler(TZ_STR)

        mock_scheduler.add_job.assert_called_once()
        # Verify CronTrigger was constructed with hour=21
        mock_cron_cls.assert_called_once_with(hour=21, minute=0, timezone=TZ_STR)

    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_starts_scheduler(self, mock_scheduler_cls):
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        result = scheduler.start_scheduler(TZ_STR)

        mock_scheduler.start.assert_called_once()
        self.assertIs(result, mock_scheduler)

    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_targets_run_nightly_sync(self, mock_scheduler_cls):
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        scheduler.start_scheduler(TZ_STR)

        call_args = mock_scheduler.add_job.call_args[0]
        self.assertIs(call_args[0], scheduler.run_nightly_sync)


class TestCheckAndRunMissedSync(unittest.TestCase):

    @patch("scheduler.run_nightly_sync")
    @patch("scheduler.threading.Thread")
    def test_check_missed_sync_runs_when_after_9pm(self, mock_thread_cls, mock_sync):
        tz = pytz.timezone(TZ_STR)
        mock_now = tz.localize(datetime(2026, 5, 12, 21, 30))

        with patch("scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            scheduler.check_and_run_missed_sync(TZ_STR)

        mock_thread_cls.assert_called_once_with(
            target=scheduler.run_nightly_sync, daemon=True
        )
        mock_thread_cls.return_value.start.assert_called_once()

    @patch("scheduler.run_nightly_sync")
    @patch("scheduler.threading.Thread")
    def test_check_missed_sync_skips_when_before_9pm(self, mock_thread_cls, mock_sync):
        tz = pytz.timezone(TZ_STR)
        mock_now = tz.localize(datetime(2026, 5, 12, 18, 0))

        with patch("scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            scheduler.check_and_run_missed_sync(TZ_STR)

        mock_thread_cls.assert_not_called()

    @patch("scheduler.run_nightly_sync")
    @patch("scheduler.threading.Thread")
    def test_check_missed_sync_runs_exactly_at_9pm(self, mock_thread_cls, mock_sync):
        tz = pytz.timezone(TZ_STR)
        mock_now = tz.localize(datetime(2026, 5, 12, 21, 0))

        with patch("scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            scheduler.check_and_run_missed_sync(TZ_STR)

        mock_thread_cls.assert_called_once()


import scheduler  # noqa: E402


if __name__ == "__main__":
    unittest.main()
