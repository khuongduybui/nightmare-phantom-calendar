# What the feature is

A Preferences window accessible from the menu bar that lets the user view and edit the most commonly changed settings: trigger time, timezone, default prep minutes, and calendar IDs. Changes are saved back to the Google Drive config file.

# Why we need it

Currently, changing any setting requires the user to manually find the config file on Google Drive and edit YAML. A preferences window makes the app self-contained for common configuration.

# Scope

The window covers only the settings most likely to need user adjustment:

| Setting | Config key | Default |
|---|---|---|
| Daily trigger time | `calendars.daily_run_time` | `21:00` |
| Timezone | `timezone` | `America/New_York` |
| Default prep minutes | `default_prep_minutes` | `30` |
| Personal calendar ID | `calendars.personal_id` | `duykbui1989@gmail.com` |
| MSI Work calendar ID | `calendars.msi_id` | `duy.bui@motorolasolutions.com` |

Settings NOT in scope for this window (managed via Drive config directly):
- Recurring meetings list
- Meeting type → prep time mapping
- Baseline event details
- Locations and client overrides

# Acceptance Criteria (testable)

**AC1 — Preferences menu item**
Given the app is running, when the user clicks the menu bar icon, then "Preferences…" appears in the dropdown (above "Run now").

**AC2 — Preferences window opens**
Given the user clicks "Preferences…", when the window opens, then it shows the 5 configurable settings with their current values pre-filled.

**AC3 — Changes saved to Drive config**
Given the user edits one or more fields and clicks "Save", when save completes, then the Drive config file is updated and the scheduler is restarted with the new trigger time/timezone.

**AC4 — Validation**
Given the user enters an invalid value (e.g. trigger time not in HH:MM format, or non-integer prep minutes), when they click "Save", then an inline error is shown and the save is blocked.

**AC5 — Cancel discards changes**
Given the user edits fields and clicks "Cancel", when the window closes, then no changes are written to the Drive config.

**AC6 — Window is modal and single-instance**
Given the preferences window is already open, when the user clicks "Preferences…" again, then the existing window is brought to the front rather than opening a second instance.

**AC7 — Preferences window runs on main thread**
Given the window is opened from the menu bar callback, it is safe to use tkinter because rumps callbacks run on the main thread (unlike the sync pipeline which uses osascript).

# System Constraints

- Window is implemented with tkinter (runs on main thread via menu callback — safe)
- Preferences window is separate from `popup.py` — lives in `preferences.py`
- Save writes the updated config via `drive_config.write_config()` and `append_recurring_meetings()` is not called (only the 5 fields above are written)
- After save, `scheduler.py`'s scheduler is restarted with the new timezone/trigger time via `app._restart_scheduler()`
- Config is re-read from Drive on each open (always shows current saved values)

# Non-goals

- Editing recurring meetings (managed via Drive config file directly)
- Editing meeting type → prep time mapping
- Editing baseline event settings
- Editing locations or client overrides
