---
spec_hash: ''
---

# NPC-0010 Spec — Preferences Window

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "trigger time" | `config["daily_run_time"]` → `CronTrigger(hour=..., minute=...)` | `drive_config.py`, `scheduler.py` |
| "timezone" | `config["timezone"]` | `drive_config.py`, `app.py::_timezone_str` |
| "default prep minutes" | `config["default_prep_minutes"]` | `drive_config.py` |
| "personal calendar ID" | `config["personal_calendar_id"]` | `drive_config.py` |
| "MSI Work calendar ID" | `config["msi_calendar_id"]` | `drive_config.py` |
| "save to Drive" | `drive_config.write_config(yaml.dump(...))` | `drive_config.py` |
| "restart scheduler" | `app._scheduler.shutdown()` + `start_scheduler(new_tz)` | `scheduler.py`, `app.py` |
| "Preferences menu item" | `rumps.MenuItem("Preferences…", callback=self.show_preferences)` | `app.py` |
| "preferences window" | `PreferencesWindow(config).show()` | `preferences.py` (to create) |

### Why tkinter is safe here

The `show_preferences` callback fires on the **main thread** (rumps schedules all menu callbacks on the main thread). Unlike `sync_job.run_nightly_sync()` which runs on a background daemon thread, a menu click callback can safely create a `tk.Tk()` window. This is the opposite of the situation in NPC-0002 where tkinter was replaced with osascript.

### Trigger time and scheduler restart

`daily_run_time` is currently read from config but `scheduler.py::start_scheduler()` hardcodes `hour=21`. The spec requires fixing `start_scheduler()` to parse `daily_run_time` from config and use it. After preferences are saved, `app._restart_scheduler(new_tz, new_trigger_time)` shuts down the current scheduler and starts a new one.

### Config serialization

`drive_config.append_recurring_meetings()` (NPC-0007) handles full YAML round-trip. For preferences, only the 5 top-level fields change. The implementation reads the current config dict from `parse_config(read_config())`, updates the 5 keys, and calls `write_config(yaml.dump(updated_data))` — same pattern as `append_recurring_meetings`.

---

## Human-Required Steps

None — all ACs are fully testable.

---

## User Stories

---

### US-1 — Preferences Window Module

**Story:** As a user, I want a tkinter preferences window I can open from the menu bar to view and edit my settings, so I don't have to edit YAML on Google Drive directly.

**Acceptance Criteria:**

- AC1.1: `preferences.py` exists at project root.
- AC1.2: `PreferencesWindow(config: dict)` is a class with a `show() -> dict | None` method that opens a tkinter window. Returns updated config dict on Save, `None` on Cancel or window close.
- AC1.3: The window displays 5 labeled Entry fields pre-populated from `config`: trigger time (HH:MM), timezone, default prep minutes, personal calendar ID, MSI calendar ID.
- AC1.4: "Save" button validates: trigger time must match `HH:MM` with `00 ≤ HH ≤ 23`, `00 ≤ MM ≤ 59`; default prep minutes must be a positive integer. Invalid entries show an inline error label and block saving. (feature.md AC4)
- AC1.5: On valid Save, returns a dict with the 5 updated values.
- AC1.6: "Cancel" button and window close (WM_DELETE_WINDOW) return `None` without saving.
- AC1.7: Window calls `self._root.lift()`, `self._root.attributes("-topmost", True)`, and `self._root.focus_force()` on open (consistent with NPC-0002 popup pattern).
- AC1.8: No `datetime.utcnow()`.

**Test coverage (`tests/test_preferences.py`):**
- `test_show_returns_none_on_cancel` — mock tk, call cancel; assert `None` returned.
- `test_show_returns_updated_config_on_save` — mock tk with valid inputs; assert returned dict has updated values.
- `test_invalid_trigger_time_blocks_save` — `"25:00"` in trigger field; assert save blocked, error shown.
- `test_invalid_prep_minutes_blocks_save` — `"abc"` in prep field; assert save blocked.
- `test_fields_pre_populated_from_config` — assert Entry widgets initialized with config values.
- `test_window_dismiss_returns_none` — WM_DELETE_WINDOW; assert `None`.

**Dependencies:** NPC-0001 (config dict shape), NPC-0002 (tkinter-on-main-thread pattern).

---

### US-2 — Wire Preferences into App + Scheduler

**Story:** As a user, I want clicking "Preferences…" to open the window and have my saved changes take effect immediately (trigger time, timezone) without restarting the app.

**Acceptance Criteria:**

- AC2.1: `app.py` adds `rumps.MenuItem("Preferences…", callback=self.show_preferences)` at the top of the menu (above status items separator). (feature.md AC1)
- AC2.2: `show_preferences(self, _)` calls `parse_config(read_config())` to get current config, then `PreferencesWindow(config).show()`. If result is not `None`, calls `_save_preferences(result)`. (feature.md AC2, AC3)
- AC2.3: `_save_preferences(self, updated: dict)` updates the Drive config file with the 5 changed fields (preserving all other config data) and calls `_restart_scheduler(updated["timezone"], updated["daily_run_time"])`. (feature.md AC3)
- AC2.4: `_restart_scheduler(self, timezone_str: str, trigger_time: str)` shuts down `self._scheduler` and calls `start_scheduler(timezone_str, trigger_time)`. (feature.md AC3)
- AC2.5: `scheduler.py::start_scheduler(timezone_str: str, trigger_time: str = "21:00")` parses `trigger_time` as HH:MM and uses it for the CronTrigger instead of the hardcoded 21. (feature.md — aligns trigger time with config)
- AC2.6: `_PREFS_OPEN: threading.Lock` module-level flag in `app.py` prevents multiple preference windows opening simultaneously. If already open, `show_preferences` returns immediately. (feature.md AC6)
- AC2.7: Error during save is logged to stderr and shown via `rumps.notification()` — non-fatal. (feature.md AC3)

**Test coverage (`tests/test_preferences_wiring.py`):**
- `test_preferences_menu_item_exists` — assert menu contains "Preferences…".
- `test_show_preferences_opens_window` — mock `PreferencesWindow.show` returning dict; assert `_save_preferences` called.
- `test_show_preferences_cancel_does_not_save` — mock returns `None`; assert `_save_preferences` not called.
- `test_save_preferences_writes_to_drive` — mock `write_config`; assert called with updated YAML.
- `test_save_preferences_restarts_scheduler` — assert old scheduler shutdown and new one started.
- `test_double_open_prevented` — lock held; second `show_preferences` call; assert `PreferencesWindow` not called twice.
- `test_start_scheduler_uses_trigger_time` — call with `trigger_time="20:00"`; assert CronTrigger at hour=20.

**Dependencies:** US-1 (`PreferencesWindow`), NPC-0004 (`start_scheduler`).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `auth.py` not modified.
- **FAC-4**: `README.md` updated — `preferences.py` in Project Structure.
- **FAC-5**: `build/tests.sh` passes without modification.

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- `preferences.py` at project root.
- tkinter used (safe — menu callbacks run on main thread).
- `scheduler.py::start_scheduler()` signature extended with `trigger_time` parameter (backward-compatible default `"21:00"`).
- Only the 5 config keys are written — all other config keys preserved.

---

## Non-Goals

- Editing recurring meetings, meeting types, baseline event, locations, client overrides.
- Multiple timezone support.
- Config file format migration.

---

## Definition of Done

- [ ] `preferences.py` created: `PreferencesWindow` with `show()`.
- [ ] `app.py` updated: "Preferences…" menu item, `show_preferences()`, `_save_preferences()`, `_restart_scheduler()`, lock guard.
- [ ] `scheduler.py` updated: `start_scheduler(timezone_str, trigger_time="21:00")`.
- [ ] `tests/test_preferences.py` — ≥ 6 cases, all passing.
- [ ] `tests/test_preferences_wiring.py` — ≥ 7 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated.
- [ ] No credentials in staged files.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 (`preferences.py`) | None | — |
| US-2 (`app.py` + `scheduler.py`) | US-1 API shape | Cannot — imports US-1 |

US-2 source can be written once `PreferencesWindow.show()` signature is fixed (fixed here). Tests cannot run until US-1 is implemented.

---

## File Touch List

### Create
- `preferences.py`
- `tests/test_preferences.py`
- `tests/test_preferences_wiring.py`

### Modify
- `app.py` — Preferences menu item, show_preferences, _save_preferences, _restart_scheduler, lock
- `scheduler.py` — `start_scheduler(timezone_str, trigger_time="21:00")`
- `README.md` — add `preferences.py` to Project Structure

### Do NOT touch
- `auth.py`, `main.py`, `requirements.txt`
- `drive_config.py`, `calendar_reader.py`, `compute.py`, `popup.py`, `calendar_writer.py`, `sync_job.py`
