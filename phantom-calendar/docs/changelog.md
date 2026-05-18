# Phantom Calendar — Changelog

## System Overview

Phantom Calendar is a macOS menu bar app that computes and writes a morning wake-up alarm to your Google Calendar every night at 9 PM. It reads your work (MSI) and personal calendars for the next day, matches time blocks to configured meeting types, and calculates exactly how early you need to be up based on each meeting's prep time. A native macOS dialog appears at 9 PM for you to confirm, adjust, or skip before anything is written to your calendar. If a meeting is rescheduled after 9 PM, you can re-run at any time via the "Run now" menu item.

**What works today (merged to main):**
- Full nightly pipeline: read calendars → compute alarm → confirm via osascript dialog → write to Google Calendar
- Automatic 9 PM daily trigger; missed-sync runs on startup if the app was closed at trigger time
- Manual "Run now" from the menu bar, with a one-deep queue if a sync is already running
- Menu bar shows last run time, last alarm time, spinner during sync, and an error badge on failure; state persists across app restarts
- Menu bar icon uses proper monochrome PNG template images (dark mode native)
- Preferences window ("Preferences…" menu item) lets you edit trigger time, timezone, prep minutes, and calendar IDs without touching Drive YAML
- Location-based travel time fully resolved: `travel+N` prep entries use `config["locations"]` travel minutes, personal calendar event locations are read, and a date override / test mode is available
- Unknown work calendar blocks can be classified during the popup; the local osaurus AI pre-selects the most likely type so you can confirm in one click — save as Recurring (written to Drive config) or One-shot (this run only)
- Personal calendar events are also offered for type classification via the same AI-assisted Recurring/One-shot flow
- Personal calendar events at unknown locations prompt for travel time during the popup; new location → travel-minute mappings are saved back to the Drive config
- On macOS with `ical-guy` installed and Calendar permission granted: all Apple Calendar events for tomorrow are read into a unified pool and used as the event source; alarm writes always go to Google Calendar; falls back silently to Google Calendar reads when ical-guy is unavailable

---

## NPC-0000 — Bootstrap
*Merged to main*

The one-time setup that makes every other feature possible.

### US-1 — Project Scaffold
- Created `requirements.txt` with all core dependencies (google-api-python-client, google-auth-oauthlib, APScheduler, rumps, pytz)
- Created `.gitignore` excluding credentials, tokens, venv, and build artifacts
- Added `tests/smoke_imports.py` to verify all packages import successfully in the venv

### US-2 — Auth Module
- `auth.py`: full Google OAuth lifecycle — first-run browser consent, token persistence (`token.json`), and silent refresh on expiry
- Exposes `get_credentials()`, `get_calendar_service()`, and `get_drive_service()`
- `token.json` written with `0o600` permissions (owner-only)
- `FileNotFoundError` raised when `credentials.json` is missing (caught and surfaced by the launcher)

### US-3 — Menu Bar App Stub
- `app.py`: `PhantomCalendarApp` with clock icon (⏰), "Run now" placeholder, and "Quit" button
- `main.py`: calls `get_credentials()` before starting the app; exits with a readable error if `credentials.json` is absent (no raw traceback shown)

---

## NPC-0001 — Decision Engine
*Merged to main*

Reads both calendars for tomorrow and computes the correct alarm time.

### US-1 — Drive Config Module
- `drive_config.py`: reads meeting configuration from a Google Drive YAML file
- `parse_config()` returns all configurable values (calendar IDs, recurring meetings, prep times, timezone, baseline event ID) with safe defaults when any key is absent
- Self-healing bootstrap: if the Drive file is empty or invalid YAML, the default `config.yaml` is written to Drive automatically
- `pyyaml==6.0.2` added to `requirements.txt`

### US-2 — Calendar Reader
- `calendar_reader.py`: `get_msi_time_blocks()` fetches tomorrow's free/busy blocks from the MSI work calendar (titles not available — free/busy reader only)
- `get_personal_events()` fetches tomorrow's full events (title, start, end) from the personal Google Calendar
- Alarm events previously written by the system are excluded from personal event results
- All times are tz-aware in the configured local timezone; `datetime.utcnow()` not used anywhere

### US-3 — Compute Engine
- `compute.py`: `compute_alarm()` matches MSI time blocks to recurring meetings in config (5-minute tolerance), resolves prep times, and returns a structured result
- Result includes: first meeting name, meeting start time, prep minutes, computed alarm time, baseline match flag, all meetings considered, and any unknown MSI blocks
- Unknown blocks (no matching config entry) flagged and returned with the default prep time applied
- Baseline match detected when the first meeting equals the configured daily standup

---

## NPC-0002 — Confirmation Popup
*Merged to main*

Gives the user a final check before anything is written to the calendar.

### US-1 — Confirmation Popup
- `popup.py`: `ConfirmationPopup(result).show()` opens a tkinter window with three display modes: normal (meeting found, editable alarm field), baseline (alarm matches the recurring baseline — no write needed), and no-meetings (empty day)
- User can edit the alarm time (format validated as HH:MM), confirm (writes to calendar), or skip (no write)
- Closing the window via the OS close button is treated as confirmation with the current alarm time value
- Unknown MSI block count displayed as a non-blocking warning when present
- Window calls `lift()`, `-topmost True`, and `focus_force()` so it appears above all other windows when triggered at 9 PM
- Returns a structured response: `{"confirmed": bool, "alarm_time": datetime|None, "skipped": bool}`

---

## NPC-0003 — Calendar Writer
*Merged to main*

Writes the confirmed alarm event to Google Calendar, safely handling the baseline recurring event.

### US-1 — Core Write Operations
- `calendar_writer.py`: `write_alarm_event()` creates a calendar event tagged with `ALARM_TAG = "phantom-calendar-alarm"` in its description so future runs can find and replace it
- Event title: `"⏰ Alarm — {meeting_name}"`; duration equals prep minutes (back-to-back with the meeting)
- `get_existing_alarm_for_tomorrow()` queries for existing tagged events; `delete_alarm_event()` removes stale ones before writing the new alarm

### US-2 — Baseline Handling + Orchestration
- `run_calendar_write()` orchestrates the full write flow: skip if response is skipped/not confirmed, delete any stale alarm, write the new alarm, then override only tomorrow's occurrence of the baseline recurring event
- Baseline future recurrences are never deleted or modified — only the specific instance for tomorrow is patched via `events().instances()` + `events().update()`
- All API failures are caught, surfaced with a readable message, and re-raised for the caller

---

## NPC-0004 — Scheduler & Nightly Sync
*Merged to main*

Runs the full pipeline automatically every evening without any user action.

### US-1 — Sync Job Module
- `sync_job.py`: `run_nightly_sync()` executes the full pipeline in order: load config → read MSI blocks → read personal events → compute alarm → show popup → write to calendar
- Protected by a `threading.Lock`; returns immediately (no duplicate run) if a sync is already in progress
- Errors caught at any pipeline stage are surfaced via `rumps.notification()` and logged to stderr; the scheduler continues running

### US-2 — Scheduler + App Wiring
- `scheduler.py`: `start_scheduler(timezone_str)` creates an APScheduler `BackgroundScheduler` with a `CronTrigger` at 21:00 local time
- `check_and_run_missed_sync(timezone_str)`: if the app starts after 9 PM, a missed sync runs immediately in a background daemon thread
- `app.py` wired: reads config on startup, calls `check_and_run_missed_sync`, starts the scheduler, and shuts it down cleanly on quit

---

## NPC-0005 — Menu Bar App
*Merged to main*

Gives the nightly automation a persistent home in the macOS menu bar with visible status.

### US-1 — Status Menu Items + Icon States
- Menu bar shows: "Last run: HH:MM AM/PM", "Alarm: HH:MM AM/PM" (or "—" before first run), "Run now", separator, "Quit"
- Icon states: ⏰ (idle), ⏳ (sync in progress), ⏰❌ (last sync failed)
- `set_syncing(True/False)` and `update_sync_state(alarm_time, failed)` update icon and menu items after each sync
- `run_nightly_sync()` now accepts an optional `app_ref` parameter; the app passes `self` so sync status is reflected in real time
- All state held in memory only (no disk persistence — addressed in NPC-0008)

### US-2 — Login Item Registration
- On first launch, the app registers itself as a macOS Login Item via `osascript` so it starts automatically on Mac login
- Registration failure is non-fatal: logged to stderr, app continues

---

## NPC-0006 — On-Demand Sync (Run Now)
*Merged to main*

Lets the user re-run the sync at any time without waiting for the next 9 PM trigger.

### US-1 — Queue Implementation
- `queue_run(app_ref=None)` in `sync_job.py`: if no sync is running, runs immediately; if one is in progress, sets a `threading.Event` (`_PENDING_RUN`) to queue exactly one follow-up run
- Queue depth is one — multiple "Run now" clicks during an active sync queue only a single follow-up (idempotent `Event.set()`)
- After each sync completes, `_PENDING_RUN` is checked in the `finally` block; if set, it is cleared and the queued sync runs immediately
- `app.py` `run_now()` updated to call `queue_run(self)` instead of calling `run_nightly_sync()` directly

---

## NPC-0007 — Unknown Meeting Classification
*Merged to main*

Closes the loop on unknown MSI blocks: classify a new recurring meeting once via a dialog during the popup, and the app remembers it for all future runs.

### US-1 — Classification UI in the Sync Popup
- When unknown MSI blocks are present, a `choose from list` osascript dialog appears for each block before the main alarm confirmation
- Type list is derived from `config["meeting_type_prep"]` (travel-time entries excluded)
- Selecting a type recalculates the alarm time live; the updated alarm is reflected in the main confirmation dialog

### US-2 — Write Classifications to Drive Config
- Confirmed classifications are appended to `recurring_meetings` in the Drive config file via `append_recurring_meetings()`
- Drive config write failure is non-fatal: logged to stderr, alarm event write is unaffected

---

## NPC-0008 — Persist Last Run State
*Merged to main*

### US-1 — State Persistence
- Last run time, last alarm time, and last sync failed flag written to `.phantom_state.json` after every sync
- On app startup, state is restored from the file so the menu shows the correct values immediately (no more "—" on every relaunch)
- Corrupt or missing state file falls back to "—" placeholders without crashing
- Error icon (⏰❌) is restored on startup if the previous sync had failed

---

## NPC-0009 — Custom Icon Design
*Merged to main*

### US-1 — Wire PNG Icons into app.py
- Replace emoji `title` strings (⏰/⏳/⏰❌) with `self.icon` pointing to monochrome PNG template images in `assets/`
- Three icons: `icon.png` (idle), `icon_syncing.png` (sync in progress), `icon_error.png` (last sync failed)
- macOS treats black-on-transparent PNGs as template images: automatically inverted for dark mode, tinted when the menu bar item is active

---

## NPC-0010 — Preferences Window
*Merged to main*

### US-1 — Preferences Window Module
- `preferences.py`: tkinter window with five editable fields: daily trigger time, timezone, default prep minutes, personal calendar ID, MSI Work calendar ID
- Current values pre-filled from Drive config on open; input validation blocks saving invalid values
- Returns updated config dict on Save, `None` on Cancel

### US-2 — Wire Preferences into App + Scheduler
- "Preferences…" menu item added above status items in the menu bar
- On Save, Drive config is updated and the scheduler is restarted with the new trigger time and timezone — changes take effect without restarting the app
- `start_scheduler()` updated to accept a `trigger_time` parameter (replaces hardcoded 21:00)
- A lock prevents opening multiple preference windows simultaneously

---

## NPC-0011 — Location-Based Travel Time
*Merged to main*

### US-1 — `resolve_prep()` and `parse_config()` Extensions
- `compute.py` `resolve_prep()` resolves `"travel+N"` prep values using `config["locations"]`: `total_prep = travel_minutes + fixed_minutes`
- `"Home": 0` injected into `config["locations"]` as a default
- Recurring meeting entries gain optional `location` and `meeting_type` fields; `calendar_reader.get_personal_events()` returns the `location` field from the Google Calendar event

### US-2 — Locations Editor in Preferences
- Preferences window gains a Locations section: add, edit, and delete location → travel-time mappings via osascript dialogs
- Changes saved to Drive config

### US-3 — Date Override / Test Mode
- A test mode that allows the date used as "tomorrow" to be overridden, enabling offline testing without waiting for an actual day boundary

---

## NPC-0012 — Unknown Personal-Event Location Prompting
*Merged to main — Feature Review PASS (166/166 tests)*

Surfaces unknown personal calendar event locations during the sync popup so you can provide travel time before the alarm is written.

### US-1 — Detect Unknown Personal-Event Locations in `compute_alarm()`
- `compute_alarm()` now collects every personal event whose `location` field is non-empty, not `"Home"`, and not a key in `config["locations"]`, returning them as `unknown_personal_locations` in the result dict
- Known locations (in `config["locations"]`) and events without a location are silently ignored
- Debug mode logs unrecognized locations to stderr

### US-2 — Surface in Popup and Write to Drive Config
- `_prompt_unknown_locations()` in `sync_job.py` shows one osascript dialog per unique unrecognized location; the dialog shows the event title and location string and prompts for travel minutes (default 0)
- Alarm time recalculates immediately if the affected event is the first meeting of the day
- Non-zero travel-minute entries are returned in `location_travel_minutes` in the popup response
- `drive_config.append_locations()` merges new location → travel-minute mappings into `config["locations"]` and writes to Drive; existing entries are not overwritten
- Location config write failure is non-fatal: logged to stderr, alarm event write unaffected

---

## NPC-0013 — AI-Assisted Meeting Classification via Osaurus
*Merged to main*

Adds a local AI assistant to pre-select the most likely meeting type when classifying unknown blocks, and extends classification to personal calendar events.

### US-1 — Extend Calendar Readers with Title and Description
- `get_msi_time_blocks()` now returns `title` (default `"Untitled"`) and `description` (default `""`) per block, enabling the AI to classify work calendar events even though MSI is free/busy reader only
- `get_personal_events()` now returns `description` (default `""`) alongside existing fields

### US-2 — Osaurus Client Module
- New `osaurus_client.py` with `suggest_meeting_type(title, description, categories)`: queries the local osaurus server (OpenAI-compatible at `127.0.0.1:1337`), validates the response against the configured category list, and returns the matched category or `None`
- No retry; any failure (connection refused, timeout, unrecognized response) returns `None` and logs one line to stderr — never blocks a sync run
- Server URL, API key, and model name read from `osaurus.yaml` (not hardcoded); API key never appears in logs
- `openai>=1.0,<3` added to `requirements.txt`

### US-3 — Wire Suggestion + Recurring/One-Shot Dialogs into Sync Popup
- Before each unknown MSI block's classification dialog, `suggest_meeting_type()` is called; if a suggestion is returned, it appears pre-selected in the `choose from list` dialog — you can confirm in one click or override
- After selecting a type (non-Skip), a second dialog asks: **"Save this for future runs?"** with options **Recurring** (saved to Drive config) or **One-shot** (alarm recalculated this run only, not written to config)
- New `_classify_personal_events()` function mirrors the same flow for personal calendar events: AI suggestion → select type → Recurring or One-shot
- Classification order: unknown MSI blocks → unknown personal locations → personal event classification
- When osaurus is unavailable, all dialogs open with no pre-selection — existing behavior is fully preserved
- All osaurus calls wrapped in `try/except` as defense-in-depth so a client bug cannot kill a sync run

---

## NPC-0014 — Apple Calendar as Event Source
*Merged to main — Feature Review PASS (239/239 tests)*

Adds Apple Calendar as a read-only event source on macOS, replacing Google Calendar for event querying when `ical-guy` is installed and Calendar permission is granted. All Apple Calendar events for tomorrow are treated as a single unified pool — no distinction between work and personal calendars. Alarm writes always go to Google Calendar. Falls back to Google Calendar reads silently when `ical-guy` is unavailable or Calendar permission is not granted.

**Bug fix (pre-existing):** Recurring meeting classifications were silently discarded on baseline days (days where the alarm already matches the configured daily standup). Fixed by removing the `confirmed` gate on the classifications save — "Recurring" intent is now persisted regardless of whether a calendar write occurred.

### US-1 — `apple_calendar.py`: Apple Calendar read module
- New `apple_calendar.py` with `is_accessible()` and `get_tomorrow_events(target_date, exclude_calendars, timezone_str)`
- `is_accessible()` checks: macOS platform, macOS ≥14, `ical-guy` binary found (probes known Homebrew paths as fallback for launchd/Finder launches where PATH is restricted), probe call exits zero with parseable JSON
- `get_tomorrow_events()` calls `ical-guy events --from DATE --exclude-all-day --format json`, converts UTC datetimes to the configured local timezone, filters events not matching `target_date` in local time, and returns a sorted `list[dict]` in the canonical `{start, end, title, description, location}` shape
- Optional `exclude_calendars` list forwarded as `--exclude-calendars` arg to `ical-guy`
- `drive_config.parse_config()` extended with `apple_exclude_calendars` key (defaults to `[]`)

### US-2 — `sync_job.py`: route reads through Apple Calendar when available
- `run_nightly_sync()` calls `apple_calendar.is_accessible()` once after `parse_config()`; when True, reads all events via `get_tomorrow_events()` and passes the unified pool to `compute_alarm()` as `msi_blocks` with `personal_events=[]`
- Events with "Alarm" in the title filtered from the Apple pool before compute (guards against Google Calendar alarms synced into Calendar.app)
- On `get_tomorrow_events()` failure: `rumps.notification` fires with the specific reason and the run falls back to Google Calendar reads; fallback is transparent to the user
- When `is_accessible()` returns False (ical-guy not installed, macOS < 14, permission denied): Google Calendar reads used silently — no notification, no behavior change
- Alarm write path (`run_calendar_write()`) unchanged — always writes to Google Calendar
- MT-14.1–MT-14.6 manual tests added to `build/manual_tests.md`
- `README.md` updated: `apple_calendar.py` in Project Structure table; "Optional Dependencies" section documenting `ical-guy` install steps
