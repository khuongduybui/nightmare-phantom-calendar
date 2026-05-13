---
spec_hash: ''
---

# NPC-0006 Spec — On-Demand Sync (Run Now)

## Clarifications from Codebase

### What NPC-0005 Already Provides

NPC-0005's `app.py` `run_now()` already calls `run_nightly_sync(app_ref=self)` in a daemon thread. The existing `_SYNC_LOCK` in `sync_job.py` prevents concurrent runs (returns immediately if locked).

NPC-0006 adds the **queue** behavior on top: instead of silently dropping the second click, it enqueues one pending run to execute after the current sync completes.

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "Run now" entry point | `PhantomCalendarApp.run_now()` | `app.py` (NPC-0005) |
| "sync already running" | `_SYNC_LOCK.locked()` | `sync_job.py` |
| "queue one pending run" | `_PENDING_RUN: threading.Event` | `sync_job.py` |
| "at most one queued" | `_PENDING_RUN.set()` (idempotent) | `sync_job.py` |
| "run immediately after" | check `_PENDING_RUN` at end of sync, re-call | `sync_job.py` |

### Key Design Decisions

1. **`threading.Event` as queue** — `_PENDING_RUN = threading.Event()` at module level. `set()` is idempotent — clicking "Run now" twice while a sync runs only queues one pending run (AC4). `clear()` + re-run at the end of each sync handles AC3.

2. **Queue check in `run_nightly_sync()`** — After `_SYNC_LOCK.release()` in the `finally` block, check `_PENDING_RUN.is_set()`. If set, clear it and call `run_nightly_sync(app_ref)` recursively (this is safe — the lock has been released so the recursive call will acquire it).

3. **`queue_run(app_ref=None)`** — New public function in `sync_job.py`. If sync is currently running (`_SYNC_LOCK.locked()`), sets `_PENDING_RUN` and returns. Otherwise, calls `run_nightly_sync(app_ref)` directly. `app.py` `run_now()` calls this instead of `run_nightly_sync` directly.

4. **AC2 (identical pipeline)** — `queue_run()` always calls `run_nightly_sync()` — no steps skipped or modified.

5. **AC5, AC6, AC7** — handled by existing `app_ref` callbacks in `sync_job.py`. No additional changes.

---

## Human-Required Steps

None — all ACs are automatable.

---

## User Stories

---

### US-1 — Queue Implementation

**Story:** As a user, I want clicking "Run now" while a sync is in progress to queue exactly one follow-up run, so that I always get a fresh result without losing my click.

**Acceptance Criteria:**

- AC1.1: `_PENDING_RUN = threading.Event()` module-level constant in `sync_job.py`.
- AC1.2: `queue_run(app_ref=None) -> None` — if `_SYNC_LOCK.locked()`, calls `_PENDING_RUN.set()` and returns. Otherwise, calls `run_nightly_sync(app_ref)` directly. (feature.md AC1, AC3)
- AC1.3: At the end of `run_nightly_sync()` (in the `finally` block, after `_SYNC_LOCK.release()`), if `_PENDING_RUN.is_set()`: clear it and call `run_nightly_sync(app_ref)`. (feature.md AC3)
- AC1.4: `_PENDING_RUN.set()` is idempotent — multiple `queue_run()` calls while locked set the event exactly once. (feature.md AC4)
- AC1.5: `app.py` `run_now()` is updated to call `queue_run(app_ref=self)` instead of `run_nightly_sync(app_ref=self)`.
- AC1.6: No `datetime.utcnow()`.

**Test coverage (`tests/test_on_demand_sync.py`):**
- `test_queue_run_calls_sync_directly_when_not_running` — lock not held; assert `run_nightly_sync` called immediately.
- `test_queue_run_sets_pending_when_running` — lock held; assert `_PENDING_RUN.is_set()` after `queue_run()`.
- `test_queue_run_does_not_double_queue` — lock held; two `queue_run()` calls; assert `_PENDING_RUN` set only once (idempotent).
- `test_pending_run_executes_after_sync_completes` — mock pipeline; assert `run_nightly_sync` called a second time after first completes when pending is set.
- `test_no_pending_run_when_not_queued` — no `queue_run()` during sync; assert not called twice.

**Dependencies:** NPC-0005 (app.py `run_now` + `sync_job.py` `app_ref` pattern).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `auth.py` not modified.
- **FAC-4**: `credentials.json` and `token.json` absent from committed files.
- **FAC-5**: `README.md` updated.
- **FAC-6**: `build/tests.sh` passes without modification.

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- `sync_job.py` and `app.py` are the only files modified.
- Queue is in-memory only — not persisted across app restarts.
- `auth.py` not modified.

---

## Non-Goals

- Any entry point other than "Run now".
- Hotkey or keyboard shortcut.
- Persisting queue across restarts.
- Queue depth > 1.

---

## Definition of Done

- [ ] `sync_job.py` updated: `_PENDING_RUN`, `queue_run()`, pending check in `run_nightly_sync`.
- [ ] `app.py` updated: `run_now` calls `queue_run`.
- [ ] `tests/test_on_demand_sync.py` — ≥ 5 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated.
- [ ] No credentials in staged files.

---

## Parallelization Analysis

Single story — no parallelism needed.

---

## File Touch List

### Modify
- `sync_job.py` — add `_PENDING_RUN`, `queue_run()`, pending check
- `app.py` — `run_now` calls `queue_run`

### Create
- `tests/test_on_demand_sync.py`

### Update
- `README.md`

### Do NOT touch
- `auth.py`, `main.py`, `requirements.txt`, `scheduler.py`
- `drive_config.py`, `calendar_reader.py`, `compute.py`, `popup.py`, `calendar_writer.py`
