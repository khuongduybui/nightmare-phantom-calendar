---
phase: QA
date: 2026-05-12
status: PASS
---

# QA Report — US-2 (Auth Module)

## AC Verification

### AC2.1 — Three public functions exported
**PASS**

`auth.py` exports:
- `get_credentials() -> google.oauth2.credentials.Credentials` ✓
- `get_calendar_service()` ✓
- `get_drive_service()` ✓

### AC2.2 — SCOPES constant
**PASS**

`SCOPES` contains exactly:
- `https://www.googleapis.com/auth/calendar` ✓
- `https://www.googleapis.com/auth/drive.file` ✓

No extra scopes present.

### AC2.3 — First run triggers browser flow and writes token
**PASS**

`get_credentials()` calls `InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)` and `flow.run_local_server(port=0)` when `token.json` is absent and `credentials.json` is present, then writes via `_write_token()`.
Covered by `test_first_run_triggers_browser_flow` — PASSED ✓

### AC2.4 — Valid token returns immediately
**PASS**

When `creds.valid` is True, `get_credentials()` returns without calling flow or refresh.
Covered by `test_valid_token_no_flow` — PASSED ✓

### AC2.5 — Expired token with refresh_token triggers refresh and rewrites token
**PASS**

When `creds.valid=False`, `creds.expired=True`, `creds.refresh_token` is not None, `get_credentials()` calls `creds.refresh(Request())` and rewrites `token.json`.
Covered by `test_expired_token_refreshes` — PASSED ✓

### AC2.6 — Missing credentials.json raises FileNotFoundError
**PASS**

`get_credentials()` raises `FileNotFoundError` when `credentials.json` does not exist. `auth.py` does not catch it — correctly propagates to `main.py`.
Covered by `test_missing_credentials_raises` — PASSED ✓

### AC2.7 — token.json written with 0o600 permissions
**PASS**

`_write_token()` calls `os.chmod(TOKEN_FILE, 0o600)` immediately after the `with open(TOKEN_FILE, 'w')` block. Verified in both `test_first_run_triggers_browser_flow` and `test_expired_token_refreshes` via `mock_chmod.assert_called_once_with(auth.TOKEN_FILE, 0o600)` ✓

## Feature-Wide AC Check

- `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` used for all path resolution ✓
- `CREDENTIALS_FILE` and `TOKEN_FILE` both derived from `BASE_DIR` — no hardcoded absolute paths ✓
- `FileNotFoundError` propagates uncaught from `auth.py` ✓

## Test Run

```
4 passed in 0.10s (Python 3.14.4)
```

All 4 required tests pass.

## Findings

None. All ACs satisfied.

## Tests Added

None required. The 4 specified tests in `tests/test_auth.py` provide complete coverage of all testable ACs.
