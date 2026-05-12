---
phase: QA
date: 2026-05-12
status: PASS
---

# QA Report — US-3 (Menu Bar App Stub)

## AC Verification

### AC3.1 — FileNotFoundError caught, readable stderr, sys.exit(1)
**PASS**

`main.py` wraps `get_credentials()` in a try/except, prints a human-readable message to `sys.stderr` including the resolved path, and calls `sys.exit(1)`. No traceback exposed.
Covered by `test_missing_credentials_exits_gracefully` — PASSED ✓

### AC3.2 — PhantomCalendarApp class definition
**PASS**

`app.py` defines `PhantomCalendarApp(rumps.App)` with:
- `name='Phantom Calendar'` ✓
- `title='⏰'` ✓
- `quit_button='Quit'` ✓

### AC3.3 — No scheduler.py import
**PASS**

`app.py` imports only `rumps`. No reference to `scheduler.py` or any other out-of-scope module. ✓

### AC3.4 — Run now menu item and stub method
**PASS**

`PhantomCalendarApp.__init__` sets `self.menu = [rumps.MenuItem('Run now', callback=self.run_now)]`.
`run_now` prints `"[Run now] triggered — sync not yet implemented."` and returns without error. ✓

### AC3.5 — ⏰ icon appears in menu bar (manual)
**PASS** — Verified by developer on 2026-05-12 with `credentials.json` present and venv active. ✓

### AC3.6 — Dropdown shows Run now and Quit (manual)
**PASS** — Verified by developer on 2026-05-12. ✓

### AC3.7 — Quit exits cleanly (manual)
**PASS** — Verified by developer on 2026-05-12. ✓

## Feature-Wide AC Check

- `main.py` uses `CREDENTIALS_FILE` imported from `auth.py` (which uses `BASE_DIR`) — no hardcoded paths ✓
- `app.py` has no path resolution needs (no file I/O) ✓
- No unhandled exception escapes when `credentials.json` missing ✓

## Test Run

```
1 passed in 0.24s (Python 3.14.4)
```

## Findings

None. All ACs satisfied (automated + manual developer verification).

## Tests Added

None required. `test_missing_credentials_exits_gracefully` in `tests/test_main.py` provides the specified coverage.
