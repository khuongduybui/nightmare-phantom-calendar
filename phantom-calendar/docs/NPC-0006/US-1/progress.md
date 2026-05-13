---
phase: Implementer
spec_hash: 'c9c39c139945'
status: NotStarted
blockers: None
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Add _PENDING_RUN = threading.Event() to sync_job.py.
- Add queue_run(app_ref=None): if locked set event, else call run_nightly_sync directly.
- Add pending check in run_nightly_sync finally block after lock release.
- Update app.py run_now to call queue_run(app_ref=self).
- Create tests/test_on_demand_sync.py with 5+ tests.
- Update README.md.
