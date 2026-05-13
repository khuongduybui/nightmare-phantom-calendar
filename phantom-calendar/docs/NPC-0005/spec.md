---
spec_hash: 'fc12be59cb39'
---

# NPC-0005 Spec — Menu Bar App

## Clarifications from Codebase

### What NPC-0004 Already Provides

NPC-0004 (`app.py`) already satisfies:
- AC1 — ⏰ icon in menu bar
- AC9 — scheduler started on launch
- AC11 — `__del__` shuts down scheduler on quit

NPC-0005 adds the remaining ACs on top of the existing `app.py`.

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "last run time" | `self._last_run_time: datetime \| None` | `app.py::PhantomCalendarApp` |
| "last computed alarm time" | `self._last_alarm_time: datetime \| None` | `app.py::PhantomCalendarApp` |
| "last sync failed" | `self._last_sync_failed: bool` | `app.py::PhantomCalendarApp` |
| "last run menu item" | `self._last_run_item: rumps.MenuItem` | `app.py` |
| "last alarm menu item" | `self._last_alarm_item: rumps.MenuItem` | `app.py` |
| "spinner during sync" | `self.title = "⏳"` | `app.py` |
| "error badge" | `self.title = "⏰❌"` | `app.py` |
| "normal icon" | `self.title = "⏰"` | `app.py` |
| "Login Item registration" | `subprocess` calling `osascript` | `app.py` |
| "sync state callback" | `update_sync_state(last_run, alarm_time, failed)` | `app.py` |
| "Run now" | `run_now(self, _)` — triggers `run_nightly_sync()` in thread | `app.py` (NPC-0004) |

### Key Design Decisions

1. **Status menu items** — Two non-clickable `rumps.MenuItem` objects at the top of the menu: one for last run time, one for last alarm time. Updated in-place via `.title` property.

2. **Icon states** — Use `self.title` (the menu bar text):
   - Normal: `"⏰"`
   - Syncing: `"⏳"`
   - Error: `"⏰❌"`

3. **`update_sync_state(last_run, alarm_time, failed)` method** — called by `sync_job.run_nightly_sync()` after each sync to update menu items and icon. `sync_job.py` imports `app` module and calls this method on the running instance. The running instance is stored as a module-level global in `app.py` so `sync_job.py` can reach it without circular imports.

4. **Alternative approach** (simpler, chosen): `sync_job.run_nightly_sync()` accepts optional callbacks. The app passes lambdas at startup: `on_start`, `on_success(alarm_time)`, `on_error`. This avoids circular imports entirely.

5. **Login Item registration** — On first launch, call `subprocess.run(["osascript", "-e", 'tell application "System Events" to make login item at end with properties {path:"/path/to/app", hidden:false}'])`. Path is resolved from `sys.executable` parent. Registered only once — skip if already present.

6. **"Run now" placeholder** — feature.md says "Run now" is a placeholder in NPC-0005 (NPC-0006 wires it). But NPC-0004 already wired it to `run_nightly_sync()`. Spec: keep the NPC-0004 wiring; NPC-0005 adds icon/status updates around it.

7. **State held in memory only** — non-goal to persist last run/alarm across restarts. Placeholders shown on first launch.

---

## Human-Required Steps

### H-1 — Login Item permission (manual, MT-5.AC10)
macOS may prompt for permission the first time the app tries to register a Login Item. Accept the prompt. Verify in System Settings → General → Login Items.

---

## User Stories

---

### US-1 — Status Menu Items + Icon States

**Story:** As a user, I want the menu to show the last sync time and alarm time, and the menu bar icon to reflect the current sync state, so I can see at a glance whether the app is running and what alarm was set.

**Acceptance Criteria:**

- AC1.1: `app.py` adds two non-clickable status menu items above "Run now": `_last_run_item` and `_last_alarm_item`. (feature.md AC2, AC3, AC4)
- AC1.2: On init, both items display placeholder text: `"Last run: —"` and `"Alarm: —"`. (feature.md AC5)
- AC1.3: `PhantomCalendarApp` stores `_last_run_time: datetime | None = None`, `_last_alarm_time: datetime | None = None`, `_last_sync_failed: bool = False`.
- AC1.4: `update_sync_state(self, alarm_time: datetime | None, failed: bool) -> None` updates:
  - `_last_run_time` = `datetime.now(local_tz)`
  - `_last_alarm_time` = `alarm_time`
  - `_last_sync_failed` = `failed`
  - `_last_run_item.title` = `f"Last run: {now.strftime('%I:%M %p')}"` (no leading zero)
  - `_last_alarm_item.title` = `f"Alarm: {alarm_time.strftime('%I:%M %p')}"` if alarm_time else `"Alarm: none"`
  - Icon: `self.title = "⏰❌"` if failed else `"⏰"`
  (feature.md AC3, AC4, AC7, AC8)
- AC1.5: `set_syncing(self, syncing: bool) -> None` sets `self.title = "⏳"` if syncing else restores based on `_last_sync_failed`. (feature.md AC6, AC7)
- AC1.6: `sync_job.run_nightly_sync()` is updated to call `app_instance.set_syncing(True)` at start and `app_instance.update_sync_state(alarm_time, failed)` at end. The running app instance is passed as an optional parameter: `run_nightly_sync(app_ref=None)`. (feature.md AC6, AC7, AC8)
- AC1.7: `run_now` in `app.py` passes `self` as `app_ref` when calling `run_nightly_sync`. The scheduler job also passes `self`.
- AC1.8: No `datetime.utcnow()`.

**Test coverage (`tests/test_app_status.py`):**
- `test_initial_status_shows_placeholders` — new app instance; assert both menu items show `"—"`.
- `test_update_sync_state_updates_last_run_item` — call `update_sync_state(alarm_time, failed=False)`; assert `_last_run_item.title` contains formatted time.
- `test_update_sync_state_updates_alarm_item` — assert `_last_alarm_item.title` shows alarm time.
- `test_update_sync_state_no_alarm` — `alarm_time=None`; assert `_last_alarm_item.title == "Alarm: none"`.
- `test_update_sync_state_failed_sets_error_icon` — `failed=True`; assert `self.title == "⏰❌"`.
- `test_update_sync_state_success_sets_normal_icon` — `failed=False`; assert `self.title == "⏰"`.
- `test_set_syncing_true_sets_spinner` — assert `self.title == "⏳"`.
- `test_set_syncing_false_restores_icon` — failed=True then set_syncing(False); assert `self.title == "⏰❌"`.

**Dependencies:** NPC-0004 (app.py already has scheduler wiring).

---

### US-2 — Login Item Registration

**Story:** As a user, I want the app to register itself as a Login Item on first launch so it starts automatically on Mac login.

**Acceptance Criteria:**

- AC2.1: `_register_login_item(self) -> None` is called once in `__init__` after the scheduler starts.
- AC2.2: `_register_login_item()` uses `subprocess.run` with `osascript` to add the app as a Login Item. The script path is derived from `os.path.abspath(sys.argv[0])`.
- AC2.3: If the `osascript` call fails (non-zero exit or exception), the error is logged to stderr and the app continues — Login Item registration failure is non-fatal. (feature.md AC10)
- AC2.4: No test for the actual osascript call (macOS-specific, cannot be isolated). AC2.3 is verified by a unit test that mocks `subprocess.run` to raise an exception and asserts the app does not crash.

**Test coverage (`tests/test_app_status.py`):**
- `test_login_item_failure_does_not_crash_app` — mock `subprocess.run` raising; assert app initializes without exception.

**Dependencies:** US-1.

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `auth.py` not modified.
- **FAC-4**: `credentials.json` and `token.json` absent from committed files.
- **FAC-5**: `README.md` updated.
- **FAC-6**: `build/manual_tests.md` updated with MT-5.AC10.

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- macOS only.
- `app.py` and `sync_job.py` are the only files modified.
- State held in memory only — no disk persistence.
- `auth.py` not modified.

---

## Non-Goals

- On-demand sync logic (NPC-0006).
- Packaging as .app (post-MVP).
- Custom icon design.
- Preferences window.
- Persisting state across restarts.

---

## Definition of Done

- [ ] `app.py` updated: status menu items, `update_sync_state()`, `set_syncing()`, `_register_login_item()`.
- [ ] `sync_job.py` updated: `run_nightly_sync(app_ref=None)` calls `set_syncing` and `update_sync_state`.
- [ ] `tests/test_app_status.py` — ≥ 9 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated.
- [ ] `build/manual_tests.md` updated with MT-5.AC10.
- [ ] No credentials in staged files.

---

## Parallelization Analysis

Single story chain — US-1 must precede US-2 (US-2 adds to `__init__` after US-1's changes).

---

## File Touch List

### Modify
- `app.py` — add status items, icon state, login item
- `sync_job.py` — add `app_ref` parameter, call `set_syncing`/`update_sync_state`

### Create
- `tests/test_app_status.py`

### Update
- `README.md`
- `build/manual_tests.md`

### Do NOT touch
- `auth.py`, `main.py`, `requirements.txt`
- `scheduler.py`, `drive_config.py`, `calendar_reader.py`, `compute.py`, `popup.py`, `calendar_writer.py`
