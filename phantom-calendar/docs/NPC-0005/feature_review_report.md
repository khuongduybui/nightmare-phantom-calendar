---
phase: Feature-Review
date: 2026-05-12
status: PASS
spec_hash: fc12be59cb39
---

# Feature Review Report — NPC-0005 (Menu Bar App)

## Definition of Done Check

| Item | Status |
|------|--------|
| `app.py` updated — status items, icon states, `update_sync_state()`, `set_syncing()`, `_register_login_item()` | ✅ |
| `sync_job.py` updated — `app_ref=None` parameter, `set_syncing`/`update_sync_state` callbacks | ✅ |
| `tests/test_app_status.py` — 10 cases, all passing | ✅ |
| `uv run python -m pytest tests/ -v` exits 0 (93/93) | ✅ |
| `README.md` updated — `test_app_status.py` listed, MT-5.AC10 in table | ✅ |
| `build/manual_tests.md` updated — MT-5.AC10 added | ✅ |
| No credentials committed | ✅ |
| `auth.py` not modified | ✅ |
| `build/tests.sh` passes without modification | ✅ |

---

## Code Review

### `app.py`
- **Status menu items** — `_last_run_item` and `_last_alarm_item` added as non-clickable items at top of menu, above a separator, above "Run now". ✓
- **Placeholder text** — `"Last run: —"` and `"Alarm: —"` on init. ✓
- **`update_sync_state(alarm_time, failed)`** — updates run time, alarm time, failed flag, menu item titles, and icon. No `datetime.utcnow()`. ✓
- **`set_syncing(syncing)`** — `⏳` when True; restores `⏰❌` or `⏰` based on `_last_sync_failed`. ✓
- **`_register_login_item()`** — `subprocess.run` with `osascript`; non-fatal (logs stderr, continues). ✓
- **`run_now`** — passes `self` as `app_ref` to `run_nightly_sync`. ✓

### `sync_job.py`
- **`app_ref=None`** parameter added — backward-compatible, existing scheduler calls without `app_ref` still work. ✓
- **`set_syncing(True)`** called before pipeline starts; `update_sync_state(alarm_time, failed)` called in `finally` after lock release. ✓
- Callbacks wrapped in `try/except` — callback failure never propagates. ✓
- `alarm_time` extracted from result before exception handling so it's available in `finally`. ✓

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
| `update-manual-tests-md` — MT-5.AC10 added | ✅ |
| `update-readme` — test file listed, MT-5.AC10 in table | ✅ |
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
| `test_app_status.py` | 10 | ✅ |
| **Total** | **93 + 5 subtests** | ✅ |

---

## Manual Tests Pending

| ID | Description |
|----|-------------|
| MT-5.AC10 | App registers as Login Item; launches on Mac login |

---

## Findings

None.

## Merge Recommendation

**APPROVED** — NPC-0005 is ready to merge to `main`.
