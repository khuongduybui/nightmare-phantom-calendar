"""Unit tests for NPC-0006: on-demand sync queue behavior."""

import threading
import unittest
from unittest.mock import MagicMock, call, patch


class TestQueueRun(unittest.TestCase):

    def setUp(self):
        # Reset module state between tests
        sync_job._PENDING_RUN.clear()
        if sync_job._SYNC_LOCK.locked():
            sync_job._SYNC_LOCK.release()

    @patch("sync_job.run_nightly_sync")
    def test_queue_run_calls_sync_directly_when_not_running(self, mock_sync):
        sync_job.queue_run()
        mock_sync.assert_called_once_with(None, target_date=None)

    def test_queue_run_sets_pending_when_running(self):
        sync_job._SYNC_LOCK.acquire()
        try:
            sync_job.queue_run()
            self.assertTrue(sync_job._PENDING_RUN.is_set())
        finally:
            sync_job._SYNC_LOCK.release()

    def test_queue_run_does_not_double_queue(self):
        sync_job._SYNC_LOCK.acquire()
        try:
            sync_job.queue_run()
            sync_job.queue_run()
            # Event is still set (not double-counted — idempotent set)
            self.assertTrue(sync_job._PENDING_RUN.is_set())
        finally:
            sync_job._SYNC_LOCK.release()

    def test_queue_run_passes_app_ref(self):
        app_ref = MagicMock()
        with patch("sync_job.run_nightly_sync") as mock_sync:
            sync_job.queue_run(app_ref=app_ref)
        mock_sync.assert_called_once_with(app_ref, target_date=None)


class TestPendingRunExecution(unittest.TestCase):

    def setUp(self):
        sync_job._PENDING_RUN.clear()
        if sync_job._SYNC_LOCK.locked():
            sync_job._SYNC_LOCK.release()

    @patch("sync_job.run_calendar_write")
    @patch("sync_job._show_popup", return_value={"confirmed": False, "alarm_time": None, "skipped": True})
    @patch(
        "sync_job.compute_alarm",
        return_value={
            "first_meeting_name": "Standup",
            "prep_minutes": 5,
            "alarm_time": MagicMock(),
            "is_baseline": False,
            "all_meetings": [],
            "unknown_blocks": [],
        },
    )
    @patch("sync_job.get_personal_events", return_value=[])
    @patch("sync_job.get_msi_time_blocks", return_value=[])
    @patch(
        "sync_job.parse_config",
        return_value={
            "timezone": "America/New_York",
            "default_prep_minutes": 30,
            "recurring_meetings": [],
        },
    )
    @patch("sync_job.read_config", return_value="yaml")
    def test_no_pending_run_when_not_queued(
        self,
        mock_read,
        mock_parse,
        mock_msi,
        mock_personal,
        mock_compute,
        mock_popup,
        mock_write,
    ):
        call_count = {"n": 0}
        original_sync = sync_job.run_nightly_sync

        def counting_sync(app_ref=None, target_date=None):
            call_count["n"] += 1
            original_sync(app_ref, target_date=target_date)

        with patch.object(sync_job, "run_nightly_sync", side_effect=counting_sync):
            sync_job.queue_run()

        self.assertEqual(call_count["n"], 1)

    def test_pending_event_cleared_after_execution(self):
        """After run_nightly_sync completes with a pending flag, flag is cleared."""
        sync_job._PENDING_RUN.set()

        with (
            patch("sync_job.read_config", side_effect=Exception("abort after first")),
            patch("sync_job.rumps"),
        ):
            # First run will fail; pending flag should be consumed and a second run attempted
            # We don't care about the second run's outcome — just that _PENDING_RUN is cleared
            sync_job.run_nightly_sync()

        self.assertFalse(sync_job._PENDING_RUN.is_set())


import sync_job  # noqa: E402

if __name__ == "__main__":
    unittest.main()
