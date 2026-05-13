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

On first launch, a browser window opens for Google OAuth sign-in. After approving, the menu bar icon appears. Subsequent launches restore the last sync status immediately from `.phantom_state.json`.

---

## Menu Bar Icons

The app uses three monochrome PNG template images that adapt automatically to macOS light/dark mode:

| File | State | Description |
|------|-------|-------------|
| `assets/icon.png` | Idle | Alarm clock with hands at ~9:00 |
| `assets/icon_syncing.png` | Sync in progress | Alarm clock with refresh arrows |
| `assets/icon_error.png` | Last sync failed | Alarm clock with exclamation badge |

**Design spec:** 36×36 px, black monochrome line art on transparent background, single stroke weight, no fill, no gradients. macOS treats these as template images (auto light/dark inversion).

To generate new icons (e.g. after new sync states are added), see [docs/NPC-0009/feature.md](docs/NPC-0009/feature.md) for the Gemini image generation prompts. All icons must share the same alarm clock base silhouette for visual consistency.

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
- Runs `pytest tests/` covering auth, Drive config, calendar reading, alarm computation, sync pipeline, and preferences

### Manual tests

See [build/manual_tests.md](build/manual_tests.md) for the full list of manual acceptance criteria, including:

| ID | Description |
|----|-------------|
| MT-1.3 | venv creation and `pip install -r requirements.txt` exits 0 |
| MT-1.4 | All packages present after install (`pip show`) |
| MT-2.11 | Confirmation dialog appears and is usable (osascript) |
| MT-4.AC1 | Popup appears automatically at 9pm (or immediately on late startup) |
| MT-5.AC10 | App registers as a Login Item and launches on Mac login |
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
├── preferences.py        Preferences window (osascript) — edit trigger time, timezone, prep minutes, calendar IDs
├── calendar_writer.py    Writes alarm event to Google Calendar; overrides baseline occurrence
├── sync_job.py           Nightly sync pipeline (config → compute → dialog → write), with lock
├── scheduler.py          APScheduler 21:00 daily trigger and missed-sync detection
├── assets/
│   ├── icon.png          Menu bar icon — idle state
│   ├── icon_syncing.png  Menu bar icon — sync in progress
│   └── icon_error.png    Menu bar icon — last sync failed
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
    ├── test_calendar_writer.py  Calendar writer unit tests
    ├── test_sync_job.py      Nightly sync pipeline unit tests
    ├── test_scheduler.py     Scheduler unit tests
    ├── test_app_status.py    App status display and login item unit tests
    └── test_on_demand_sync.py  On-demand sync queue unit tests
```

---

## Security Notes

- `credentials.json` and `token.json` are excluded from git by `.gitignore`.
- `token.json` is written with `chmod 600` (owner read/write only).
- OAuth scopes are minimal: Calendar read/write and Drive file access only.
