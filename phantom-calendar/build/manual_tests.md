# Phantom Calendar — Manual Tests

This file lists every manual acceptance criterion that cannot be automated.
Complete all prerequisites before running each section.

---

## Prerequisites

- Python 3.14 installed (`python3.14 --version` → `Python 3.14.x`)
- venv created and dependencies installed (run once from anywhere inside the repo):
  ```fish
  cd phantom-calendar
  uv venv --python 3.14 (dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv
  source (dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv/bin/activate.fish
  uv pip install -r requirements.txt
  ```
- `credentials.json` placed at `phantom-calendar/credentials.json`
  (obtained from Google Cloud Console — see README.md for setup steps)

---

## NPC-0001 — Decision Engine

### MT-1001.H2 — MSI calendar freeBusyReader access (H-2)

**Feature:** NPC-0001

**Steps:**
1. Confirm `duy.bui@motorolasolutions.com` has granted the authenticated Google account at least `freeBusyReader` permission on the MSI Work calendar.
2. With venv active, run a quick smoke: `uv run python -c "from calendar_reader import get_msi_time_blocks; print(get_msi_time_blocks())"` (requires valid `token.json`).

**Pass criteria:** Returns a list (possibly empty) without raising a permissions error.

---

## NPC-0005 — Menu Bar App

### MT-5.AC10 — App registers as Login Item (AC10)

**Feature:** NPC-0005

**Prerequisites:** App launched at least once with valid credentials.

**Steps:**
1. Launch the app:
   ```fish
   uv run main.py
   ```
2. Open **System Settings → General → Login Items & Extensions**.
3. Look for "main" or "Phantom Calendar" in the **Open at Login** list.

**Pass criteria:** The app appears in the Login Items list. On next Mac login, it starts automatically (verify by logging out and back in).

---

## NPC-0004 — Scheduler & Nightly Sync

### MT-4.AC1 — Popup appears automatically at 9pm (AC1, AC3)

**Feature:** NPC-0004

**Prerequisites:** All of NPC-0000 through NPC-0003 complete; valid `token.json`; `credentials.json` present; Drive config file accessible.

**Steps (test at 9pm):**
1. With venv active, from `phantom-calendar/`:
   ```fish
   uv run main.py
   ```
2. Wait for 21:00 local time.
3. Observe whether the confirmation popup appears automatically without clicking anything.

**Pass criteria:** Popup appears at 21:00 without user interaction. ⏰ icon remains in menu bar after popup is closed.

**Steps (test missed sync):**
1. Ensure the app is NOT running at 21:00.
2. After 21:00, launch the app:
   ```fish
   uv run main.py
   ```
3. Observe whether the popup appears within a few seconds of launch.

**Pass criteria:** Popup appears shortly after launch (missed sync detected and run immediately). App does not show the popup again at the next 21:00 — only the following day's trigger fires.

---

## NPC-0002 — Confirmation Popup

### MT-2.11 — Popup appears in front and claims focus (AC1.11)

**Feature:** NPC-0002 / US-1

**Prerequisites:** NPC-0001 complete; valid `token.json` present; venv active.

**Steps:**
1. Open several other apps (browser, editor) so they cover the terminal.
2. With venv active, from `phantom-calendar/`, trigger the popup manually:
   ```fish
   uv run python -c "
   from datetime import date, datetime, timedelta
   import pytz
   from popup import ConfirmationPopup
   tz = pytz.timezone('America/New_York')
   d = date.today() + timedelta(days=1)
   result = {
     'first_meeting_name': 'Test Meeting',
     'first_meeting_time': tz.localize(datetime(d.year, d.month, d.day, 9, 30)),
     'prep_minutes': 10,
     'alarm_time': tz.localize(datetime(d.year, d.month, d.day, 9, 20)),
     'is_baseline': False,
     'all_meetings': [],
     'unknown_blocks': [],
   }
   print(ConfirmationPopup(result).show())
   "
   ```
3. Observe whether the popup window appears above all other open windows.
4. Observe whether the popup window has keyboard focus (you can type in the alarm field immediately without clicking).

**Pass criteria:** Popup appears on top of all other windows; keyboard focus is on the popup immediately (alarm field is active or window title bar is highlighted).

---

## NPC-0000 — Bootstrap

### MT-1.3 — Venv creation and dependency install (AC1.3)

**Feature:** NPC-0000 / US-1

**Steps:**
1. From `phantom-calendar/` (fish shell):
   ```fish
   source (dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv/bin/activate.fish
   uv pip install -r requirements.txt
   ```
2. Confirm the command exits with code 0 and no error output.

**Pass criteria:** Exit code 0, no `ERROR` or `WARNING` lines in output.

---

### MT-1.4 — All packages present after install (AC1.4)

**Feature:** NPC-0000 / US-1

**Steps:**
1. With venv active (fish), run:
   ```fish
   uv pip show rumps google-api-python-client google-auth-oauthlib APScheduler pytz
   ```
2. Confirm all 5 packages are listed with a `Name:` and `Version:` entry.

**Pass criteria:** 5 `Name:` entries shown, versions match `requirements.txt`.

---

### MT-3.5 — Menu bar icon appears (AC3.5)

**Feature:** NPC-0000 / US-3

**Steps:**
1. Ensure `credentials.json` is present at `phantom-calendar/credentials.json`.
2. With venv active, from `phantom-calendar/`:
   ```bash
   uv run main.py
   ```
3. On first run, a browser window will open for Google OAuth sign-in. Complete the sign-in flow.
4. After sign-in, look at the macOS menu bar (top-right area).

**Pass criteria:** ⏰ icon is visible in the macOS menu bar.

---

### MT-3.6 — Dropdown shows Run now and Quit (AC3.6)

**Feature:** NPC-0000 / US-3

**Prerequisites:** MT-3.5 complete (app running with ⏰ in menu bar).

**Steps:**
1. Click the ⏰ icon in the menu bar.
2. Observe the dropdown menu.

**Pass criteria:** Dropdown contains at minimum "Run now" and "Quit" items.

---

### MT-3.7 — Quit exits cleanly (AC3.7)

**Feature:** NPC-0000 / US-3

**Prerequisites:** MT-3.6 complete (dropdown visible).

**Steps:**
1. Click "Quit" in the dropdown.
2. Observe the terminal where `uv run main.py` was launched.

**Pass criteria:** App exits with code 0. No error output or traceback in terminal.

---

## Adding New Manual Tests

When a new feature introduces manual ACs:
1. Add a new `## Feature-Name` section above.
2. Each test gets a unique ID: `MT-{feature_number}.{ac_number}` (e.g., `MT-2.1`).
3. Include: Feature, Prerequisites, Steps, Pass criteria.
4. Update `README.md` to reference any new setup steps.
