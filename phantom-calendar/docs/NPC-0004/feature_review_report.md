---
phase: Feature-Review
date: 2026-05-12
status: PASS
spec_hash: 90b7d00b6727
---

# Feature Review Report — NPC-0004 (Scheduler & Nightly Sync)

## Definition of Done Check

| Item | Status |
|------|--------|
| `sync_job.py` created with `run_nightly_sync()`, lock, error surfacing | ✅ |
| `scheduler.py` created with `start_scheduler()`, `check_and_run_missed_sync()` | ✅ |
| `app.py` updated — config load, missed sync, scheduler start, `run_now` wired | ✅ |
| `tests/test_sync_job.py` — 6 cases, all passing | ✅ |
| `tests/test_scheduler.py` — 6 cases, all passing | ✅ |
| `uv run python -m pytest tests/ -v` exits 0 (83/83) | ✅ |
| `README.md` updated — `sync_job.py`, `scheduler.py`, new test files, MT-4.AC1 | ✅ |
| `build/manual_tests.md` updated — MT-4.AC1 added | ✅ |
| No credentials committed | ✅ |
| `requirements.txt` unchanged (APScheduler already present) | ✅ |
| `auth.py` not modified | ✅ |
| `build/tests.sh` passes without modification | ✅ |

---

## Code Review

### `sync_job.py`
- **Pipeline order** — `read_config → parse_config → get_msi_time_blocks → get_personal_events → compute_alarm → ConfirmationPopup.show() → run_calendar_write()` ✓
- **Lock** — module-level `threading.Lock`, `acquire(blocking=False)` at start; released in `finally`. No concurrent runs. ✓
- **Error handling** — `try/except` wraps entire pipeline; `rumps.notification()` (wrapped in its own try) + stderr; no re-raise. ✓
- **`run_calendar_write`** called with `meeting_name=result["first_meeting_name"]` and `prep_minutes=result["prep_minutes"]`. ✓
- No `datetime.utcnow()`. ✓

### `scheduler.py`
- **`start_scheduler(timezone_str)`** — `BackgroundScheduler` + `CronTrigger(hour=21, minute=0, timezone=timezone_str)` + `scheduler.start()`. ✓
- **`check_and_run_missed_sync(timezone_str)`** — `datetime.now(tz).hour >= 21`; fires in daemon thread if true. ✓
- Trigger hardcoded at hour=21 (non-goal: not configurable in this feature). ✓

### `app.py`
- `__init__` loads config (with fallback on error), calls `check_and_run_missed_sync()`, calls `start_scheduler()`, stores `self._scheduler`. ✓
- `__del__` shuts down scheduler with `wait=False`. ✓
- `run_now` fires `run_nightly_sync()` in daemon thread (was a print stub in NPC-0000). ✓

---

## Policy Compliance

| Policy | Status |
|--------|--------|
| No `datetime.utcnow()` | ✅ |
| No hardcoded IDs | ✅ |
| `auth.py` not modified | ✅ |
| `credentials.json` / `token.json` excluded | ✅ |
| Python 3.14 compatible | ✅ |
| Fish shell / uv conventions | ✅ |

## Rune Compliance

| Rule | Status |
|------|--------|
| `update-build-tests-sh` — auto-discovery unchanged | ✅ |
| `update-manual-tests-md` — MT-4.AC1 added | ✅ |
| `update-readme` — new files and MT-4.AC1 added | ✅ |
| `no-credentials-in-git` — confirmed absent | ✅ |
| `python-version-compatibility` — no removed APIs | ✅ |
| `venv-and-uv-conventions` — all correct | ✅ |

---

## Test Summary

| Suite | Count | Result |
|-------|-------|--------|
| `test_auth.py` | 4 | ✅ |
| `test_main.py` | 1 | ✅ |
| `test_drive_config.py` | 12 | ✅ |
| `test_calendar_reader.py` | 8 | ✅ |
| `test_compute.py` | 12 | ✅ |
| `test_popup.py` | 19 + 5 subtests | ✅ |
| `test_calendar_writer.py` | 15 | ✅ |
| `test_sync_job.py` | 6 | ✅ |
| `test_scheduler.py` | 6 | ✅ |
| **Total** | **83 + 5 subtests** | ✅ |

---

## Manual Tests Pending

| ID | Description |
|----|-------------|
| MT-4.AC1 | Popup appears at 21:00 automatically; missed sync runs on late startup |

---

## Findings

None.

## Merge Recommendation

**APPROVED** — NPC-0004 is ready to merge to `main`.
