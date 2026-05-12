---
phase: Story-Review
date: 2026-05-12
status: PASS
---

# Story Review Report — US-2 (Auth Module)

## AC Verification

| AC | Status | Evidence |
|----|--------|---------|
| AC2.1 | ✅ PASS | `get_credentials()`, `get_calendar_service()`, `get_drive_service()` all present and public |
| AC2.2 | ✅ PASS | `SCOPES` has exactly 2 entries: `calendar` and `drive.file` |
| AC2.3 | ✅ PASS | `InstalledAppFlow.from_client_secrets_file` + `run_local_server(port=0)` + `_write_token()` on first run |
| AC2.4 | ✅ PASS | Returns immediately when `creds.valid` is True |
| AC2.5 | ✅ PASS | `creds.refresh(Request())` + `_write_token()` on expired+refresh_token path |
| AC2.6 | ✅ PASS | `FileNotFoundError` raised when `credentials.json` absent; not caught in `auth.py` |
| AC2.7 | ✅ PASS | `os.chmod(TOKEN_FILE, 0o600)` immediately after `with open(TOKEN_FILE, 'w')` in `_write_token()` |

## Policy Compliance

- `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` — all paths derived from it ✓
- No hardcoded absolute paths ✓
- `FileNotFoundError` propagates uncaught — `main.py` will handle (per spec) ✓
- No `scheduler.py`, `calendar_reader.py`, or other out-of-scope files created ✓

## Test Results

4/4 passed (`test_first_run_triggers_browser_flow`, `test_valid_token_no_flow`, `test_expired_token_refreshes`, `test_missing_credentials_raises`) on Python 3.14.4.

## QA Findings Carried Over

None. QA status: PASS, no findings.

## Outcome

PASS — approved for merge to NPC-0000 feature branch.
