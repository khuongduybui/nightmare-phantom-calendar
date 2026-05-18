---
phase: QA
spec_hash: 'af1261cf8a16'
status: Done
blockers: None
---

## Last Run
- ruff check sync_job.py tests/test_sync_job.py — PASS
- python -m pytest tests/ — 239/239 PASS

## Changes Since Last Iteration
- Added `import apple_calendar` and `from datetime import date` to `sync_job.py`
- Modified `run_nightly_sync()`: updated docstring; added `use_apple = apple_calendar.is_accessible()` read source selection; branching read block calling `apple_calendar.get_tomorrow_events()` when accessible, filtering "Alarm" events from unified pool, falling back to Google reads with `rumps.notification` on RuntimeError
- Added `TestRunNightlySyncAppleCalendarRouting` with 7 tests covering all AC2 paths
- Added MT-14.1–MT-14.6 to `build/manual_tests.md`
- Updated `README.md`: `apple_calendar.py` in Project Structure table + test listing; "Optional Dependencies" section for ical-guy

## Next Steps
- Story-Review loop
