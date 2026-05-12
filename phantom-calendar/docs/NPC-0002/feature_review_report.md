---
phase: Feature-Review
date: 2026-05-12
status: PASS
spec_hash: a56b1060543e
---

# Feature Review Report — NPC-0002 (Confirmation Popup)

## Definition of Done Check

| Item | Status |
|------|--------|
| `popup.py` at project root with `ConfirmationPopup` class and `show()` method | ✅ |
| All ACs 1.1–1.10 verified by automated tests | ✅ |
| AC1.11 verified by manual test MT-2.11 | ✅ |
| `tests/test_popup.py` — 19 tests + 5 subtests, all passing | ✅ |
| `tests/smoke_imports.py` updated (pyyaml added, popup/tkinter removed) | ✅ |
| `build/manual_tests.md` — MT-2.11 entry added | ✅ |
| `README.md` — popup.py in Project Structure, MT-2.11 in manual tests table | ✅ |
| No credentials or token files staged | ✅ |
| `build/tests.sh` passes without modification | ✅ |
| 56/56 full test suite passing | ✅ |

---

## Code Review

### `popup.py`

- **3 display modes** correctly derived from result dict: normal, baseline, no-meetings. Check order (None name → baseline → normal) matches spec. ✓
- **`show()` response** always exactly 3 keys: `confirmed`, `alarm_time`, `skipped`. ✓
- **`_parse_alarm_override()`** explicit args (not `self._entry.get()`) — directly unit-testable. Validates HH:MM, rejects out-of-range. ✓
- **`_on_confirm()`** blocks on invalid entry, shows inline error, does not call `destroy()`. ✓
- **`_on_skip()`** returns `skipped=False` in baseline mode (correct — user acknowledged but no write needed), `skipped=True` otherwise. ✓
- **`WM_DELETE_WINDOW`** bound to `_on_confirm` in normal mode, `_on_skip` in others. ✓
- **Unknown blocks warning** lists each block's start time as `HH:MM` — one line per block. ✓
- **Focus**: osascript activates process, `after(100, entry.focus_set)` focuses Entry once event loop starts. ✓
- **Keyboard**: Entry `<Return>` → confirm; buttons have `takefocus=True`, `<Return>` and `<space>` bindings. ✓
- **Lazy tkinter import** — `popup.py` importable without Tk installed (tested in CI). ✓
- **Isolation** — no imports of `auth`, `calendar_reader`, `drive_config`, or `compute`. ✓
- **No `sys.exit()`**. ✓

---

## Manual Test MT-2.11

| Check | Result |
|-------|--------|
| Window jumps to front from other apps | ✅ PASS |
| Alarm Entry field has keyboard cursor on open | ✅ PASS |
| Enter key submits from Entry | ✅ PASS |
| Tab navigates Entry → Write to Calendar → Skip | ✅ PASS |
| Space/Enter activates focused button | ✅ PASS |

---

## Policy Compliance

| Policy | Status |
|--------|--------|
| No `datetime.utcnow()` | ✅ |
| No hardcoded configurable values | ✅ |
| `auth.py` not modified | ✅ |
| `credentials.json` / `token.json` excluded | ✅ |
| Python 3.14 compatible | ✅ |
| Fish shell / uv conventions in docs | ✅ |
| `scheduler.py`, `calendar_writer.py`, `sync_job.py` not created | ✅ |

## Rune Compliance

| Rule | Status |
|------|--------|
| `update-build-tests-sh` — auto-discovery unchanged | ✅ |
| `update-manual-tests-md` — MT-2.11 added | ✅ |
| `update-readme` — popup.py and MT-2.11 added | ✅ |
| `no-credentials-in-git` — confirmed absent | ✅ |
| `python-version-compatibility` — no removed APIs | ✅ |
| `venv-and-uv-conventions` — docs use uv/fish | ✅ |

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
| **Total** | **56 + 5 subtests** | ✅ |

---

## Findings

None.

## Merge Recommendation

**APPROVED** — NPC-0002 is ready to merge to `main`.
