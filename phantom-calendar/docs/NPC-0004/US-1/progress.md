---
phase: Implementer
spec_hash: 'c45b782ee969'
status: NotStarted
blockers: None
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Create sync_job.py: module-level threading.Lock, run_nightly_sync() with full pipeline call chain.
- Pipeline: read_config() → parse_config() → get_msi_time_blocks() → get_personal_events() → compute_alarm() → ConfirmationPopup.show() → run_calendar_write(response, config, meeting_name, prep_minutes).
- Lock: if already held, return immediately (no concurrent run).
- Error handling: catch all exceptions, rumps.notification() + stderr, do not re-raise.
- Create tests/test_sync_job.py with ≥4 mocked tests.
