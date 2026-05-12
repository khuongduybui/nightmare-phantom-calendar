# Phantom Calendar

A macOS menu bar app that syncs Google Calendar events to Google Drive.

---

## Requirements

- macOS (required — uses `rumps` which is macOS-only)
- Python 3.14
- Google Cloud project with Calendar API and Drive API enabled

---

## First-Time Setup

### 1. Install Python 3.14

Download from https://www.python.org/downloads/ and verify:

```bash
python3.14 --version
```

### 2. Create and activate a virtual environment

```bash
python3.14 -m venv .venv
source .venv/bin/activate        # bash/zsh
# or: source .venv/bin/activate.fish  # fish shell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Google Cloud credentials

1. Go to https://console.cloud.google.com and create a project named **Phantom Calendar**.
2. Enable **Google Calendar API** and **Google Drive API** under "APIs & Services".
3. Go to "Credentials" → "Create Credentials" → "OAuth client ID".
   - Application type: **Desktop app**
   - Name: **Phantom Calendar Desktop**
4. Download the JSON file and rename/place it at:
   ```
   phantom-calendar/credentials.json
   ```
   > ⚠️ `credentials.json` is excluded from git by `.gitignore`. Never commit it.
5. Go to "OAuth consent screen":
   - User type: External
   - Add your Gmail as a test user
   - Add scopes: `https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/drive.file`

---

## Running the App

```bash
python main.py
```

On first launch, a browser window opens for Google OAuth sign-in. After approving, the ⏰ icon appears in the macOS menu bar.

Subsequent launches use the cached token at `token.json` (also excluded from git).

---

## Testing

### Automated tests

Run all unit tests and smoke imports with:

```bash
bash build/tests.sh
```

This script:
- Verifies the venv is active
- Runs `tests/smoke_imports.py` (confirms all packages importable)
- Runs `pytest tests/` (37 unit tests covering auth, Drive config, calendar reading, and alarm computation)

### Manual tests

See [build/manual_tests.md](build/manual_tests.md) for the full list of manual acceptance criteria, including:

| ID | Description |
|----|-------------|
| MT-1.3 | venv creation and `pip install -r requirements.txt` exits 0 |
| MT-1.4 | All packages present after install (`pip show`) |
| MT-2.11 | Confirmation popup appears above all windows and claims focus |
| MT-3.5 | ⏰ icon appears in macOS menu bar |
| MT-3.6 | Dropdown shows "Run now" and "Quit" |
| MT-3.7 | "Quit" exits cleanly with code 0 |

---

## Project Structure

```
phantom-calendar/
├── auth.py               OAuth lifecycle (credentials, token, refresh)
├── app.py                macOS menu bar app (rumps)
├── main.py               Entry point
├── drive_config.py       Google Drive config read/parse/bootstrap (YAML)
├── calendar_reader.py    Reads MSI time blocks and Personal calendar events
├── compute.py            Matches meetings and computes alarm time
├── popup.py              Confirmation popup (tkinter) — user reviews and confirms alarm
├── config.yaml           Default configuration (committed; auto-pushed to Drive)
├── requirements.txt      Pinned runtime dependencies
├── .gitignore            Excludes credentials.json, token.json, .venv/, etc.
├── build/
│   ├── tests.sh          Run all automated tests
│   └── manual_tests.md   Manual acceptance criteria
└── tests/
    ├── smoke_imports.py      Import smoke test
    ├── test_auth.py          Auth module unit tests
    ├── test_main.py          Entry point unit tests
    ├── test_drive_config.py  Drive config unit tests
    ├── test_calendar_reader.py  Calendar reader unit tests
    ├── test_compute.py       Compute module unit tests
    └── test_popup.py         Confirmation popup unit tests
```

---

## Security Notes

- `credentials.json` and `token.json` are excluded from git by `.gitignore`.
- `token.json` is written with `chmod 600` (owner read/write only).
- OAuth scopes are minimal: Calendar read/write and Drive file access only.
