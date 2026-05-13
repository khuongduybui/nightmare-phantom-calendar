---
phase: Feature-Review
date: 2026-05-12
status: PASS
spec_hash: c9c39c139945
---

# Feature Review Report — NPC-0006 (On-Demand Sync)

## Definition of Done Check

| Item | Status |
|------|--------|
| `sync_job.py` updated — `_PENDING_RUN`, `queue_run()`, pending check in `finally` | ✅ |
| `app.py` updated — `run_now` calls `queue_run` | ✅ |
| `tests/test_on_demand_sync.py` — 6 cases, all passing | ✅ |
| `uv run python -m pytest tests/ -v` exits 0 (99/99) | ✅ |
| `README.md` updated — `test_on_demand_sync.py` listed | ✅ |
| No credentials committed | ✅ |
| `auth.py` not modified | ✅ |

## Code Review

### `sync_job.py`
- **`_PENDING_RUN = threading.Event()`** — module-level, reset between tests. ✓
- **`queue_run(app_ref=None)`** — if `_SYNC_LOCK.locked()`, `_PENDING_RUN.set()` (idempotent → AC4); else `run_nightly_sync(app_ref)` directly (→ AC1, AC2). ✓
- **Pending check** — in `finally` after `_SYNC_LOCK.release()`: if set → `clear()` + `run_nightly_sync(app_ref)`. Lock is free before recursive call — no deadlock. ✓
- **AC2 (identical pipeline)** — `queue_run` always calls `run_nightly_sync` — same function, same args. ✓
- **AC5, AC6, AC7** — `app_ref` callbacks already handle these from NPC-0005. ✓

### `app.py`
- `run_now` now calls `queue_run(app_ref=self)` in daemon thread instead of `run_nightly_sync`. ✓

---

## Test Summary

| Suite | Count | Result |
|-------|-------|--------|
| Previous suites | 93 | ✅ |
| `test_on_demand_sync.py` | 6 | ✅ |
| **Total** | **99 + 5 subtests** | ✅ |

## Findings

None.

## Merge Recommendation

**APPROVED** — NPC-0006 ready to merge to `main`.
