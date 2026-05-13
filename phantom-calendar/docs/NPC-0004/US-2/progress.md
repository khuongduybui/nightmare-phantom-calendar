---
phase: Implementer
spec_hash: 'c45b782ee969'
status: NotStarted
blockers: US-1
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Create scheduler.py: start_scheduler(timezone_str) → BackgroundScheduler with CronTrigger(hour=19); check_and_run_missed_sync(timezone_str).
- Modify app.py: PhantomCalendarApp.__init__() loads config, calls check_and_run_missed_sync(), calls start_scheduler(), stores as self._scheduler.
- Create tests/test_scheduler.py with ≥4 mocked tests.
- Update README.md and build/manual_tests.md (MT-4.AC1).
