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
