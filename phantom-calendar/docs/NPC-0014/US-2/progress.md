---
phase: Implementer
spec_hash: 'af1261cf8a16'
status: NotStarted
blockers: US-1
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized

## Next Steps
- After US-1 is merged: add `import apple_calendar` to `sync_job.py`
- Replace the event-read block in `run_nightly_sync()` with the branching logic that selects Apple Calendar reads when `apple_calendar.is_accessible()` is true, falling back to Google reads on any `RuntimeError` with a `rumps.notification`
- Filter out events with "Alarm" in title from the unified Apple pool before passing to `compute_alarm()`
- Pass the unified Apple pool as `msi_blocks` and `[]` as `personal_events` to `compute_alarm()`
- Extend `tests/test_sync_job.py` with the 6 routing test cases listed in spec
- Add MT-14 entries (1–6) to `build/manual_tests.md`
- Update `README.md`: list `apple_calendar.py` in Project Structure and `ical-guy` as optional runtime dependency
