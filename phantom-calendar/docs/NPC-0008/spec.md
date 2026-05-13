---
spec_hash: ''
---

# NPC-0008 Spec — Persist Last Run State

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "state file" | `.phantom_state.json` | `phantom-calendar/.phantom_state.json` |
| "last_run_time" | `app._last_run_time: datetime \| None` | `app.py::PhantomCalendarApp` |
| "last_alarm_time" | `app._last_alarm_time: datetime \| None` | `app.py::PhantomCalendarApp` |
| "error state" | `app._last_sync_failed: bool` | `app.py::PhantomCalendarApp` |
| "save on sync completion" | called from `update_sync_state()` | `app.py` |
| "load on startup" | called in `__init__()` before scheduler | `app.py` |
| "state file location" | `os.path.join(BASE_DIR, ".phantom_state.json")` | `app.py` |

### What NPC-0005 Already Provides

- `update_sync_state(alarm_time, failed)` — updates in-memory state and menu items
- `_last_run_time`, `_last_alarm_time`, `_last_sync_failed` — in-memory fields
- `_last_run_item`, `_last_alarm_item` — rumps menu items that display status

NPC-0008 adds:
1. `_save_state()` — write current state to `.phantom_state.json`
2. `_load_state()` — read state from `.phantom_state.json` on startup, update menu items

### State File Format

```json
{
  "last_run_time": "2026-05-12T21:02:34.123456-04:00",
  "last_alarm_time": "2026-05-13T09:25:00-04:00",
  "last_sync_failed": false
}
```

`null` values allowed for `last_run_time` and `last_alarm_time`.

---

## Human-Required Steps

None.

---

## User Stories

---

### US-1 — State Persistence

**Story:** As a user, I want the app to remember the last sync time and alarm time across restarts, so the menu bar shows accurate status immediately on launch.

**Acceptance Criteria:**

- AC1.1: `STATE_FILE = os.path.join(BASE_DIR, ".phantom_state.json")` is a module-level constant in `app.py`.
- AC1.2: `_save_state(self) -> None` writes `last_run_time`, `last_alarm_time`, `last_sync_failed` to `STATE_FILE` as JSON. Datetimes serialized as ISO 8601 strings; `None` serialized as JSON `null`. Errors are caught and logged to stderr — save failure is non-fatal. (feature.md AC1)
- AC1.3: `update_sync_state()` calls `_save_state()` after updating in-memory fields. (feature.md AC1)
- AC1.4: `_load_state(self) -> None` reads `STATE_FILE`, deserializes datetimes (preserving timezone), updates `_last_run_time`, `_last_alarm_time`, `_last_sync_failed`, and refreshes `_last_run_item.title` and `_last_alarm_item.title` using the same format as `update_sync_state()`. (feature.md AC2)
- AC1.5: `_load_state()` is called in `__init__()` after menu items are created but before the scheduler starts. (feature.md AC2)
- AC1.6: If the state file is missing, unreadable, or malformed JSON, `_load_state()` logs to stderr and returns without changing in-memory state (menus stay at `"—"` placeholders). (feature.md AC5)
- AC1.7: If `last_sync_failed` is `true` in the saved state, `self.title` is set to `"⏰❌"` on load. (feature.md AC6)
- AC1.8: `STATE_FILE` path (`.phantom_state.json`) is added to `.gitignore`. (feature.md AC3)
- AC1.9: No `datetime.utcnow()`.

**Test coverage (`tests/test_state_persistence.py`):**
- `test_save_state_writes_json` — call `update_sync_state(alarm_time, failed=False)`; assert `.phantom_state.json` created with correct ISO strings.
- `test_save_state_handles_none_alarm` — `alarm_time=None`; assert JSON has `null` for `last_alarm_time`.
- `test_load_state_restores_menu_items` — write state file; create new app instance; assert `_last_run_item` and `_last_alarm_item` titles not `"—"`.
- `test_load_state_sets_error_icon_on_failed` — write state with `last_sync_failed: true`; assert `self.title == "⏰❌"`.
- `test_load_state_missing_file_does_not_crash` — no state file; assert app initializes cleanly with placeholder text.
- `test_load_state_corrupt_file_does_not_crash` — malformed JSON in state file; assert no exception.
- `test_save_state_failure_is_non_fatal` — mock `open` to raise; assert `update_sync_state` does not propagate exception.

**Dependencies:** NPC-0005 (app.py state fields and menu items).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `.phantom_state.json` in `.gitignore`.
- **FAC-4**: `auth.py` not modified.
- **FAC-5**: `build/tests.sh` passes without modification.

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- Only `app.py` and `.gitignore` are modified.
- `sync_job.py`, `scheduler.py`, `drive_config.py` are NOT modified.
- State file is local only — never uploaded anywhere.

---

## Non-Goals

- Custom icon design.
- Preferences / settings window.
- Syncing state across machines.

---

## Definition of Done

- [ ] `app.py` updated: `STATE_FILE`, `_save_state()`, `_load_state()`, `update_sync_state()` calls save, `__init__` calls load.
- [ ] `.gitignore` updated: `.phantom_state.json` added.
- [ ] `tests/test_state_persistence.py` — ≥ 7 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `build/tests.sh` passes.

---

## Parallelization Analysis

Single story — no parallelism needed.

---

## File Touch List

### Modify
- `app.py`
- `.gitignore`

### Create
- `tests/test_state_persistence.py`
