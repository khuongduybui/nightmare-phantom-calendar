---
phase: QA
date: 2026-05-12
status: PASS
---

# QA Report — US-1 (Project Scaffold)

## AC Verification

### AC1.1 — requirements.txt packages and versions
**PASS**

`requirements.txt` contains exactly the 6 required packages at the correct pinned versions:
```
google-api-python-client==2.126.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
APScheduler==3.10.4
rumps==0.4.0
pytz==2024.1
```
`pyinstaller` is absent. No extra packages present.

### AC1.2 — .gitignore exclusions
**PASS**

`.gitignore` contains all required entries:
- `credentials.json` ✓
- `token.json` ✓
- `__pycache__/` ✓
- `*.pyc` ✓
- `dist/` ✓
- `build/` ✓
- `*.spec` ✓
- `.venv/` ✓

### AC1.3 — venv creation and pip install
**PASS (manual — verified by developer)**

`python3.14 -m venv .venv` and `uv pip install -r requirements.txt` completed with exit code 0 on Python 3.14.4. venv located at `/Users/duybui/code/nightmare/phantom-calendar/.venv/`.

### AC1.4 — packages present after install
**PASS (manual — verified by developer)**

`uv pip show rumps google-api-python-client google-auth-oauthlib APScheduler pytz` returned all 5 packages at correct versions under Python 3.14.4.

### AC1.5 — tests/smoke_imports.py
**PASS**

Script imports all 5 required packages (`rumps`, `googleapiclient`, `google_auth_oauthlib`, `apscheduler`, `pytz`) via `__import__()`, prints `OK: <name>` per success, prints `FAIL: <name> — <exc>` to stderr on `ImportError`, exits 1 if any failure else 0.

Ran `uv run tests/smoke_imports.py` with venv active — all 5 packages OK, exit code 0.

## Feature-Wide AC Check

- `BASE_DIR` — N/A for US-1 files (no Python modules with path resolution).
- `credentials.json` / `token.json` excluded from git — confirmed in `.gitignore` ✓.

## Findings

None. All ACs satisfied.

## Tests Added

None required. AC1.5 (`smoke_imports.py`) provides the automated coverage for this story.
