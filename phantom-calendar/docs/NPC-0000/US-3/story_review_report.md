---
phase: Story-Review
date: 2026-05-12
status: PASS
---

# Story Review Report — US-3 (Menu Bar App Stub)

## AC Verification

| AC | Status | Evidence |
|----|--------|---------|
| AC3.1 | ✅ PASS | `main.py` catches `FileNotFoundError`, prints readable message to stderr, calls `sys.exit(1)` |
| AC3.2 | ✅ PASS | `PhantomCalendarApp(rumps.App)` with `name='Phantom Calendar'`, `title='⏰'`, `quit_button='Quit'` |
| AC3.3 | ✅ PASS | `app.py` imports only `rumps` — no `scheduler.py` reference |
| AC3.4 | ✅ PASS | `rumps.MenuItem('Run now', callback=self.run_now)` in menu; stub logs and returns |
| AC3.5 | ✅ PASS (manual) | Developer verified ⏰ icon appears in menu bar |
| AC3.6 | ✅ PASS (manual) | Developer verified dropdown shows "Run now" and "Quit" |
| AC3.7 | ✅ PASS (manual) | Developer verified "Quit" exits cleanly |

## Policy Compliance

- No hardcoded absolute paths — `CREDENTIALS_FILE` sourced from `auth.py` via `BASE_DIR` ✓
- `scheduler.py` not imported or referenced ✓
- No unhandled exception escapes when `credentials.json` missing ✓
- `credentials.json` not committed (covered by `.gitignore`) ✓

## Test Results

1/1 passed (`test_missing_credentials_exits_gracefully`) on Python 3.14.4.

## QA Findings Carried Over

None. QA status: PASS, all ACs verified.

## Outcome

PASS — approved for merge to NPC-0000 feature branch.
