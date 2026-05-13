---
spec_hash: 'c45b782ee969'
---

# NPC-0004 Spec — Scheduler & Nightly Sync

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "full sync pipeline" | `run_nightly_sync()` | `sync_job.py` (to create) |
| "load config" | `drive_config.read_config()` + `parse_config()` | `drive_config.py` |
| "read calendars" | `calendar_reader.get_msi_time_blocks()`, `get_personal_events()` | `calendar_reader.py` |
| "compute alarm" | `compute.compute_alarm()` | `compute.py` |
| "show confirmation popup" | `popup.ConfirmationPopup(result).show()` | `popup.py` |
| "write to calendar" | `calendar_writer.run_calendar_write()` | `calendar_writer.py` |
| "scheduler" | `APScheduler BackgroundScheduler` | `scheduler.py` (to create) |
| "9pm trigger" | `CronTrigger(hour=19, minute=0, timezone=LOCAL_TZ)` | `scheduler.py` |
| "missed sync detection" | compare `datetime.now(LOCAL_TZ).hour >= 19` at startup | `scheduler.py` |
| "app launch" | `PhantomCalendarApp.__init__()` | `app.py` (modify) |
| "surface error" | `rumps.notification(...)` or `print(..., file=sys.stderr)` | `sync_job.py` |

### Key Design Decisions

1. **`sync_job.py`** — the sync pipeline function `run_nightly_sync()`. Orchestrates the full flow: read_config → parse_config → get_msi_time_blocks → get_personal_events → compute_alarm → ConfirmationPopup.show() → run_calendar_write(). Standalone module with no UI.

2. **`scheduler.py`** — starts a `BackgroundScheduler` with a daily `CronTrigger` at 19:00 local time. Exposes `start_scheduler()` → returns the scheduler instance.

3. **Missed sync detection** — at startup, check if current local time ≥ 19:00. If yes, run the sync immediately in a background thread, then schedule normally. "Already ran today" is not tracked — if the app starts after 9pm, it always runs once. This satisfies AC3 and AC4 (no repeat after that single startup run; next trigger is the following day's 9pm).

4. **AC5 (no double trigger)** — use a `threading.Lock` in `sync_job.py`. `run_nightly_sync()` acquires the lock at start; returns immediately if already held. This prevents concurrent runs whether triggered by scheduler or missed-sync startup.

5. **AC7 (failure isolation)** — `run_nightly_sync()` wraps the full pipeline in `try/except`. On error: surfaces via `rumps.notification()` (title "Phantom Calendar", message = error str) and logs to stderr. Does NOT re-raise — the scheduler continues.

6. **`app.py` changes** — `PhantomCalendarApp.__init__()` calls `start_scheduler()` and stores the result. This is the wiring NPC-0000 deliberately left out.

7. **Trigger time** — hardcoded `hour=19, minute=0`. Not configurable (AC6 / non-goal). Uses `config["timezone"]` for the cron timezone — read once at scheduler start.

8. **Config read timing** — config is read fresh on each sync run (not cached) so Drive config changes take effect at the next 9pm.

---

## Human-Required Steps

### H-1 — Live scheduler test (manual, MT-4.AC1)
After implementing, run `uv run main.py` and verify the popup appears at 9pm or immediately if launched after 9pm. Cannot be automated without freezing system time.

---

## User Stories

---

### US-1 — Sync Job Module

**Story:** As the scheduler, I want a `run_nightly_sync()` function that executes the full pipeline and surfaces errors without crashing, so that the nightly sync can be called reliably at any time.

**Acceptance Criteria:**

- AC1.1: `sync_job.py` exists at project root.
- AC1.2: `run_nightly_sync()` executes in order: `read_config()` → `parse_config()` → `get_msi_time_blocks()` → `get_personal_events()` → `compute_alarm()` → `ConfirmationPopup(result).show()` → `run_calendar_write(response, config, meeting_name, prep_minutes)`. (feature.md AC2)
- AC1.3: `run_nightly_sync()` is protected by a module-level `threading.Lock`. If already running, returns immediately without starting a concurrent pipeline. (feature.md AC5)
- AC1.4: If any pipeline step raises an exception, `run_nightly_sync()` catches it, calls `rumps.notification("Phantom Calendar", "", str(exc))`, prints to `sys.stderr`, and returns without re-raising. (feature.md AC7)
- AC1.5: `run_calendar_write()` is called with `meeting_name=result["first_meeting_name"]` and `prep_minutes=result["prep_minutes"]`.
- AC1.6: No `datetime.utcnow()`. All timezone-aware datetimes.

**Test coverage (`tests/test_sync_job.py`):**
- `test_run_nightly_sync_calls_pipeline_in_order` — mock all pipeline steps; assert call order.
- `test_run_nightly_sync_no_concurrent_run` — lock held; assert second call returns without executing pipeline.
- `test_run_nightly_sync_surfaces_error_on_exception` — mock `read_config` raising; assert `rumps.notification` called and no re-raise.
- `test_run_calendar_write_called_with_meeting_name_and_prep` — assert `run_calendar_write` receives `meeting_name` and `prep_minutes` from compute result.

**Dependencies:** NPC-0001, NPC-0002, NPC-0003 (all present in worktree).

---

### US-2 — Scheduler + App Wiring

**Story:** As the app, I want a scheduler that triggers `run_nightly_sync()` every day at 9pm local time and runs a missed sync on startup if 9pm has already passed, so that the user never has to manually trigger the sync.

**Acceptance Criteria:**

- AC2.1: `scheduler.py` exists at project root.
- AC2.2: `start_scheduler(timezone_str: str) -> BackgroundScheduler` creates a `BackgroundScheduler`, adds a `CronTrigger(hour=19, minute=0, timezone=timezone_str)` job targeting `run_nightly_sync`, starts the scheduler, and returns it. (feature.md AC1, AC6)
- AC2.3: `check_and_run_missed_sync(timezone_str: str) -> None` checks `datetime.now(pytz.timezone(timezone_str)).hour >= 19`. If true, runs `run_nightly_sync()` in a `threading.Thread(daemon=True)`. (feature.md AC3, AC4)
- AC2.4: `PhantomCalendarApp.__init__()` in `app.py` is updated to:
  - Read timezone from config (call `parse_config(read_config())` once at startup)
  - Call `check_and_run_missed_sync(timezone_str)`
  - Call `start_scheduler(timezone_str)` and store the result as `self._scheduler`
  (feature.md AC1, AC3)
- AC2.5: `PhantomCalendarApp.__del__()` (or `application_support` quit hook) shuts down `self._scheduler` gracefully. (feature.md AC7 — scheduler must not crash on quit)
- AC2.6: Scheduler job failures do not crash the scheduler — APScheduler's default `misfire_grace_time` and exception handling are sufficient; no additional wrapper needed beyond `sync_job.py`'s internal try/except. (feature.md AC7)

**Test coverage (`tests/test_scheduler.py`):**
- `test_start_scheduler_adds_cron_job` — mock BackgroundScheduler; assert `add_job` called with CronTrigger at hour=19.
- `test_start_scheduler_starts_scheduler` — assert `scheduler.start()` called.
- `test_check_missed_sync_runs_when_after_9pm` — mock `datetime.now()` returning 21:00; assert `run_nightly_sync` called in thread.
- `test_check_missed_sync_skips_when_before_9pm` — mock `datetime.now()` returning 18:00; assert `run_nightly_sync` NOT called.

**Dependencies:** US-1 (`run_nightly_sync`).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: `requirements.txt` unchanged — APScheduler already present.
- **FAC-3**: `credentials.json` and `token.json` absent from committed files.
- **FAC-4**: No `datetime.utcnow()`.
- **FAC-5**: `auth.py` not modified.
- **FAC-6**: `README.md` updated to add `sync_job.py` and `scheduler.py` to Project Structure table.
- **FAC-7**: `build/tests.sh` passes without modification.
- **FAC-8**: `build/manual_tests.md` updated with MT-4.AC1 (live 9pm trigger test).

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- Fish shell, uv conventions.
- macOS only.
- `sync_job.py` and `scheduler.py` at project root.
- Trigger time 19:00 hardcoded — not configurable in this feature.
- `auth.py` must not be modified.
- All API calls mocked in unit tests.

---

## Non-Goals

- Configurable trigger time.
- Weekday-only scheduling.
- On-demand / manual sync trigger (NPC-0005).
- System-level scheduling (launchd, cron).
- Retry logic for failed syncs.

---

## Definition of Done

- [ ] `sync_job.py` created: `run_nightly_sync()` with lock, pipeline, error handling.
- [ ] `scheduler.py` created: `start_scheduler()`, `check_and_run_missed_sync()`.
- [ ] `app.py` updated: `__init__` calls config load, missed sync check, scheduler start.
- [ ] `tests/test_sync_job.py` — ≥ 4 cases, all passing.
- [ ] `tests/test_scheduler.py` — ≥ 4 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated.
- [ ] `build/manual_tests.md` updated with MT-4.AC1.
- [ ] No credentials in staged files.
- [ ] `build/tests.sh` passes without modification.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 (`sync_job.py`) | None (pipeline modules all present) | — |
| US-2 (`scheduler.py` + `app.py`) | US-1 (`run_nightly_sync`) | Cannot parallelize |

---

## File Touch List

### Create
```
phantom-calendar/
├── sync_job.py
├── scheduler.py
└── tests/
    ├── test_sync_job.py
    └── test_scheduler.py
```

### Modify
- `app.py` — add config load, missed sync check, scheduler start to `__init__`
- `README.md` — add `sync_job.py`, `scheduler.py` to Project Structure
- `build/manual_tests.md` — add MT-4.AC1

### Do NOT touch
- `auth.py`, `main.py`, `requirements.txt`
- `drive_config.py`, `calendar_reader.py`, `compute.py`, `popup.py`, `calendar_writer.py`
- `build/tests.sh`
