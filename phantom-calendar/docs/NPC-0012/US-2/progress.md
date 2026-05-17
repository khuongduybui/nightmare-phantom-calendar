---
phase: QA
spec_hash: '75972f8a557d'
status: Done
blockers: None
---

## Last Run
- ruff check sync_job.py drive_config.py tests/test_sync_job.py — PASS
- bash build/tests.sh — PASS (166/166)

## Changes Since Last Iteration
- Added `_prompt_unknown_locations()` to `sync_job.py`: groups unknown personal event locations, shows one osascript dialog per unique location, returns `(location_travel_minutes, updated_alarm_time)`
- Updated `_show_popup()` to call `_prompt_unknown_locations()` when `result["unknown_personal_locations"]` is non-empty and not baseline; added `location_travel_minutes` to all return paths
- Updated `run_nightly_sync()` to call `append_locations()` after `append_recurring_meetings` block (non-fatal, same try/except pattern)
- Added `append_locations(location_travel_minutes, config)` to `drive_config.py`: merges new entries (existing not overwritten), writes full config YAML to Drive
- Added 20 new tests in `tests/test_sync_job.py` covering AC 2.4–2.11 (TestPromptUnknownLocations, TestShowPopupLocationTravelMinutes, TestAppendLocations, TestRunNightlySyncWritesLocations)

## Next Steps
- QA loop then Story-Review loop until both return `PASS`
