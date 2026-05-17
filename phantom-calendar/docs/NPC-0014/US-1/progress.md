---
phase: Implementer
spec_hash: 'af1261cf8a16'
status: NotStarted
blockers: None
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized

## Next Steps
- Implement `apple_calendar.py`: `is_accessible()` (macOS/version/PATH/probe checks) and `get_tomorrow_events(target_date, exclude_calendars)` returning canonical event dicts from all Apple Calendars via ical-guy
- Extend `drive_config.parse_config()` with `apple_exclude_calendars` key (defaults to `[]`)
- Write `tests/test_apple_calendar.py` (mock `subprocess.run`, `shutil.which`, `platform.system`, `platform.mac_ver`)
- Extend `tests/test_drive_config.py` with `apple_exclude_calendars` parsing tests
