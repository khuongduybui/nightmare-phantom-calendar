---
phase: Story-Review
spec_hash: 'c9c39c139945'
status: StoryReviewPassed
blockers: None
---

## Last Run
- 2026-05-12: Implemented, QA'd, Story-Reviewed US-1 — added _PENDING_RUN, queue_run() to sync_job.py; updated app.py run_now; created tests/test_on_demand_sync.py. 6/6 tests; 99/99 full suite.

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Add _PENDING_RUN = threading.Event() to sync_job.py.
- Add queue_run(app_ref=None): if locked set event, else call run_nightly_sync directly.
- Add pending check in run_nightly_sync finally block after lock release.
- Update app.py run_now to call queue_run(app_ref=self).
- Create tests/test_on_demand_sync.py with 5+ tests.
- Update README.md.
