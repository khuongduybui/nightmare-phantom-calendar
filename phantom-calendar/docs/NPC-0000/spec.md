---
spec_hash: '77dde19595b0'
---

# NPC-0000 Spec — Phantom Calendar Bootstrap

## Clarifications from Codebase

This is a greenfield project. No existing source to search. All mappings derived from `project.md` (the build-plan reference attached to feature.md).

| feature.md term | Code identifier | Location |
|---|---|---|
| "virtual environment" | `.venv/` at project root | `python3.14 -m venv .venv` |
| "all declared dependencies" | `requirements.txt` | project root |
| `credentials.json` | `CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')` | `auth.py` |
| `token.json` | `TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')` | `auth.py` |
| "browser window opens for sign-in" | `flow.run_local_server(port=0)` | `auth.py::get_credentials()` |
| "menu bar icon" | `rumps.App(title='⏰')` | `app.py::PhantomCalendarApp` |
| "Run now" menu item | `rumps.MenuItem('Run now', callback=self.run_now)` | `app.py` |
| "Quit" button | `quit_button='Quit'` in `rumps.App.__init__()` | `app.py` |
| "exits gracefully with readable error" | `sys.exit(1)` + `print(..., file=sys.stderr)` | `main.py` |
| "app is launched" | `python main.py` | project root |
| `BASE_DIR` path anchor | `os.path.dirname(os.path.abspath(__file__))` | all modules |

**Mismatches flagged (feature.md wins):**
- feature.md requires Python 3.14; project.md says 3.11+. Spec targets 3.14.
- project.md includes `pyinstaller` in `requirements.txt`. NPC-0000 explicitly excludes `.app` packaging — `pyinstaller` must NOT appear in `requirements.txt` for this feature.
- project.md's `app.py` calls `start_scheduler()` from `scheduler.py` (not yet created). NPC-0000 `app.py` must be a stub that does not import `scheduler.py`.

---

## ⚠️ Human-Required Steps Before AI Can Run or Test Anything

These steps cannot be automated. The developer must complete all of them and place the named file at the named location before running or testing the app. AI can write all source code without these, but the app cannot be launched until they are done.

### Step H-1 — Install Python 3.14
- Install Python 3.14 on the macOS machine.
- Confirm: `python3.14 --version` prints `Python 3.14.x`.
- Required before: running `python3.14 -m venv .venv` (US-1 manual verification).

### Step H-2 — Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click "New Project" → name it "Phantom Calendar" → Create.
- Required before: H-3 and H-4.

### Step H-3 — Enable APIs
1. Go to "APIs & Services" → "Enable APIs and Services".
2. Enable **Google Calendar API**.
3. Enable **Google Drive API**.
- Required before: H-4.

### Step H-4 — Create OAuth Credentials and Configure Consent Screen
1. Go to "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID".
2. Application type: **Desktop app**. Name: "Phantom Calendar Desktop".
3. Download the JSON file.
4. Go to "OAuth consent screen":
   - User type: External.
   - App name: "Phantom Calendar".
   - Add `duykbui1989@gmail.com` as a test user.
   - Add scopes: `https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/drive.file`.

### 📦 Deliverable — Place credentials.json
**After step H-4, place the downloaded file at:**
```
/Users/duybui/code/nightmare/phantom-calendar/credentials.json
```
**This is the exact path that `auth.py` resolves via `BASE_DIR`.** Do not rename it. Do not commit it (`.gitignore` covers it). This file is the gate that allows AC2 and AC3 to be verified.

---

## User Stories (Dependency Order)

---

### US-1 — Project Scaffold

**Story:** As a developer, I want `requirements.txt` and `.gitignore` created so that I can create a virtual environment, install all dependencies cleanly, and be confident secrets are excluded from source control.

**Acceptance Criteria:**

- AC1.1: `requirements.txt` lists these packages at the versions from project.md — `google-api-python-client==2.126.0`, `google-auth-oauthlib==1.2.0`, `google-auth-httplib2==0.2.0`, `APScheduler==3.10.4`, `rumps==0.4.0`, `pytz==2024.1` — and does NOT include `pyinstaller`.
- AC1.2: `.gitignore` excludes at minimum: `credentials.json`, `token.json`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `*.spec`, `.venv/`.
- AC1.3: `python3.14 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` completes with exit code 0 and no error output. (Manual verification — requires H-1 complete.)
- AC1.4: After install, `pip show rumps google-api-python-client google-auth-oauthlib APScheduler pytz` shows all packages present. (Manual verification.)
- AC1.5: A `tests/smoke_imports.py` script exists that imports `rumps`, `googleapiclient`, `google_auth_oauthlib`, `apscheduler`, `pytz` and exits with code 0 if all succeed, or prints a named failure and exits 1. Running `python tests/smoke_imports.py` inside the venv passes.

**Test coverage expectation:** AC1.5 provides the automated import smoke check. ACs 1.3 and 1.4 are manual.

**Dependencies:** None. Can start immediately once AI takes over.

---

### US-2 — Auth Module

**Story:** As a developer, I want `auth.py` to handle the full OAuth lifecycle — first-run browser consent, token persistence, silent refresh — and surface a clear error when `credentials.json` is absent.

**Acceptance Criteria:**

- AC2.1: `auth.py` exports three public functions: `get_credentials() -> google.oauth2.credentials.Credentials`, `get_calendar_service()`, `get_drive_service()`.
- AC2.2: `SCOPES` constant in `auth.py` includes exactly `https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/drive.file`.
- AC2.3: When `token.json` does not exist and `credentials.json` exists, `get_credentials()` invokes `InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)` and calls `flow.run_local_server(port=0)`, then writes the resulting credentials as JSON to `token.json`.
- AC2.4: When `token.json` exists and `creds.valid` is True, `get_credentials()` returns without invoking any flow or refresh.
- AC2.5: When `token.json` exists, `creds.valid` is False, `creds.expired` is True, and `creds.refresh_token` is not None, `get_credentials()` calls `creds.refresh(Request())` and rewrites `token.json`.
- AC2.6: When `credentials.json` does not exist, `get_credentials()` raises `FileNotFoundError`. (`main.py` is responsible for catching this and exiting gracefully — see US-3 AC3.1.)
- AC2.7: `token.json` is written with file permissions `0o600` (owner read/write only). Implementation: `os.chmod(TOKEN_FILE, 0o600)` immediately after the `with open(TOKEN_FILE, 'w')` block.

**Test coverage expectation:** `tests/test_auth.py` using `unittest.mock`:
- `test_first_run_triggers_browser_flow`: mock `os.path.exists` (token absent, creds present), mock `InstalledAppFlow`, mock `open`, assert flow called and token written.
- `test_valid_token_no_flow`: mock `Credentials.from_authorized_user_file` returning valid creds, assert no flow or refresh invoked.
- `test_expired_token_refreshes`: mock expired creds with refresh_token, assert `creds.refresh()` called and token rewritten.
- `test_missing_credentials_raises`: mock `os.path.exists` returning False for credentials.json, assert `FileNotFoundError` raised.

**Dependencies:** US-1 (packages must be installable for tests to run).

---

### US-3 — Menu Bar App Stub

**Story:** As a developer, I want `app.py` and `main.py` to start a macOS menu bar app showing ⏰ with "Run now" and "Quit" items, and exit cleanly with a readable message if `credentials.json` is absent.

**Acceptance Criteria:**

- AC3.1: `main.py` calls `get_credentials()` before invoking the rumps app entry point. If `get_credentials()` raises `FileNotFoundError`, `main.py` catches it, prints a human-readable message to `sys.stderr` (e.g., `"Error: credentials.json not found at <path>. See README for setup instructions."`), and calls `sys.exit(1)`. No Python traceback is shown to the user.
- AC3.2: `app.py` defines `PhantomCalendarApp(rumps.App)` with `name='Phantom Calendar'`, `title='⏰'`, `quit_button='Quit'`.
- AC3.3: `PhantomCalendarApp.__init__()` does NOT import or reference `scheduler.py` (not created in this feature). The scheduler wiring is out of scope.
- AC3.4: The menu includes `rumps.MenuItem('Run now', callback=self.run_now)`. The `run_now` method is a stub that logs `"[Run now] triggered — sync not yet implemented."` and returns without error.
- AC3.5 (manual): When launched with valid setup (`credentials.json` present, venv active), `python main.py` shows the ⏰ icon in the macOS menu bar.
- AC3.6 (manual): Clicking ⏰ shows a dropdown containing at least "Run now" and "Quit".
- AC3.7 (manual): Clicking "Quit" exits the app cleanly (exit code 0).

**Test coverage expectation:** `tests/test_main.py`:
- `test_missing_credentials_exits_gracefully`: mock `get_credentials` to raise `FileNotFoundError`, capture `sys.stderr`, assert `sys.exit(1)` raised and stderr contains a readable message (not a raw traceback).

ACs 3.5, 3.6, 3.7 are manual macOS verification steps.

**Dependencies:** US-1, US-2.

---

## Feature-Wide Acceptance Criteria

- All Python modules resolve file paths via `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` — no hardcoded absolute paths.
- `credentials.json` and `token.json` are absent from all git-tracked files. `.gitignore` must be committed before any other file.
- OAuth scopes in `auth.py` exactly match the scopes configured on the GCP consent screen (neither more nor fewer).
- No unhandled exception escapes to the terminal when `credentials.json` is missing.

---

## Constraints

- macOS only — `rumps` is macOS-exclusive; no cross-platform shim needed.
- Python 3.14 — do not use deprecated APIs removed in 3.14 (e.g., `datetime.utcnow()` was removed in 3.12+; use `datetime.now(tz=timezone.utc)` instead).
- `venv` required — no `pip install` into system Python.
- Do not create `scheduler.py`, `calendar_reader.py`, `calendar_writer.py`, `drive_config.py`, `compute.py`, `popup.py`, or `sync_job.py` in this feature.

---

## Non-Goals

- Packaging as `.app` bundle (belongs to Menu Bar App feature).
- Adding to macOS Login Items (belongs to Menu Bar App feature).
- Automated GCP project creation.
- Multi-user or team setup.
- Linux or Windows support.
- Any calendar reading, writing, or alarm computation.

---

## Definition of Done

- [ ] `.gitignore` committed first, before any credential files exist.
- [ ] `requirements.txt` committed (no `pyinstaller`).
- [ ] `auth.py` committed with all ACs 2.1–2.7 satisfied.
- [ ] `app.py` and `main.py` committed with all ACs 3.1–3.4 satisfied.
- [ ] `tests/smoke_imports.py`, `tests/test_auth.py`, `tests/test_main.py` committed and passing in venv.
- [ ] Human steps H-1 through H-4 complete, `credentials.json` placed at project root.
- [ ] Manual verification: AC1.3, AC1.4, AC3.5, AC3.6, AC3.7 confirmed by developer.
- [ ] No `credentials.json` or `token.json` in git log.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 | None | — |
| US-2 | US-1 (packages) | US-3 source files can be written in parallel; cannot run/test in parallel |
| US-3 | US-1, US-2 | — |

US-2 and US-3 source files can be written in parallel (different files, no shared state). They cannot be run or tested in parallel — US-3's test imports `main.py` which imports `auth.py`.

Human steps H-1 through H-4 can run in parallel with AI writing all stories.

---

## Proposed Schema Changes

None. This project has no database.

---

## Proposed Architecture Changes

None. This is the initial bootstrap — there is no existing architecture to change.

---

## File Touch List

Every file the implementer may create or modify for NPC-0000:

```
phantom-calendar/
├── requirements.txt          (US-1 — create)
├── .gitignore                (US-1 — create)
├── auth.py                   (US-2 — create)
├── app.py                    (US-3 — create)
├── main.py                   (US-3 — create)
└── tests/
    ├── __init__.py           (US-2 — create, empty)
    ├── smoke_imports.py      (US-1 — create)
    ├── test_auth.py          (US-2 — create)
    └── test_main.py          (US-3 — create)
```

No other files should be created in this feature. `scheduler.py`, `calendar_reader.py`, `calendar_writer.py`, `drive_config.py`, `compute.py`, `popup.py`, and `sync_job.py` are out of scope.
