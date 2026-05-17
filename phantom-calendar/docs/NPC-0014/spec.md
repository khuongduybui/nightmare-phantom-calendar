---
feature: NPC-0014
spec_hash: 'af1261cf8a16'
---

# ⚠️ Human Prerequisites (complete before approving this spec)

These steps cannot be automated. They must be done by the developer on the target machine before implementation begins and before the manual tests can be run.

---

**1. Install ical-guy**

```
brew install itspriddle/brews/ical-guy
```

Without this, Apple Calendar reads are unavailable and the system silently falls back to reading events from Google Calendar (existing behavior).

> **macOS 14 (Sonoma) or later required.** ical-guy uses EventKit APIs available only on macOS 14+. On older macOS versions, `ical-guy` will not run and the system silently uses Google Calendar reads.

---

**2. Grant macOS Calendar permission**

After installing ical-guy, run `ical-guy calendars` once in a terminal and accept the macOS "Allow access to Calendar" prompt. Or pre-grant via:

> System Settings → Privacy & Security → Calendars → enable for Terminal (or whichever process invokes the app)

Calendar permission is granted to the process tree that invokes `ical-guy`. If permission is later revoked, the system silently falls back to Google Calendar reads.

---

**3. (Optional) Decide which Apple Calendars to exclude**

By default, all events from all Apple Calendars accessible to ical-guy are read into one unified pool for tomorrow. If certain calendars should be excluded (e.g., "US Holidays", "Birthdays", subscription calendars), note their exact names as they appear in Calendar.app.

---

**4. (Optional) Add the exclusion config key to `config.yaml` / Drive config**

Under the existing `calendars:` section, add:

```yaml
calendars:
  # ... existing keys ...
  apple_exclude_calendars:
    - "US Holidays"
    - "Birthdays"
```

If `apple_exclude_calendars` is absent or empty, no calendars are excluded — all Apple Calendar events go into the unified pool. Google Calendar config keys (`personal_id`, `msi_id`) remain required for alarm writes regardless of whether Apple reads are active.

---

# Clarifications from Codebase

| Feature.md term | Codebase reality |
|---|---|
| "unified event pool" | A single `list[dict]` with the same shape as `get_msi_time_blocks()`: `{start: datetime, end: datetime, title: str, description: str, location: str \| None}` — fed into `compute_alarm()` as the `msi_blocks` argument with `personal_events=[]` |
| "compute pipeline" | `compute.compute_alarm(msi_blocks, personal_events, config)` — unchanged in this feature; recurring-meeting matching and unknown-block classification continue to work because unified events pass through the existing `msi_blocks` path |
| "Apple Calendar read source" | New module `apple_calendar.py` exposing `is_accessible()` and `get_tomorrow_events(target_date, exclude_calendars)` |
| "Google Calendar read source" | Existing `get_msi_time_blocks()` and `get_personal_events()` in `calendar_reader.py` — unchanged |
| "alarm write path" | `calendar_writer.run_calendar_write()` — **completely unchanged**, always writes to Google Calendar via the existing OAuth-authenticated client |
| "ical-guy" | Third-party Swift CLI (`brew install itspriddle/brews/ical-guy`); binary is `ical-guy`; read-only EventKit access; invoked via `subprocess.run(["ical-guy", ...])`; JSON output via `--format json` |
| "fallback notification" | `rumps.notification("Phantom Calendar", "", msg)` — same pattern as existing error notification in `sync_job.py` |
| "no persistent state files" | Only `config.yaml`, `token.json`, `.drive_config_id`, `.phantom_state.json` are persistent — Apple Calendar event data must not appear in any of these |
| `platform.system()` | Used to detect macOS: `platform.system() == "Darwin"`. macOS version check: `platform.mac_ver()[0]` returns a version string like `"14.4.1"` |
| "alarm events excluded from event pool" | Existing `sync_job.run_nightly_sync()` filters `personal_events = [e for e in personal_events if "Alarm" not in e.get("title", "")]` — for Apple reads, the same filter applies to the unified pool before passing to compute (alarm events live in Google Calendar but if the user has Google Calendar synced into Calendar.app, they will appear in the Apple read and must be filtered out) |

---

# User Stories

## US-1 — `apple_calendar.py`: Apple Calendar read module

### Description
Create `phantom-calendar/apple_calendar.py` with two public functions: `is_accessible()` to detect whether ical-guy can read Apple Calendar on this machine, and `get_tomorrow_events(target_date, exclude_calendars)` to return tomorrow's events from all Apple Calendars as a unified list in the canonical event-dict shape used by the compute pipeline. Extend `drive_config.parse_config()` to extract the new `apple_exclude_calendars` config key.

### Acceptance Criteria

**AC1.1 — `is_accessible()` returns False on non-macOS**
Given `platform.system() != "Darwin"`, when `is_accessible()` is called, then it returns `False` without invoking any subprocess.

**AC1.2 — `is_accessible()` returns False when macOS version < 14**
Given the app is running on macOS but `platform.mac_ver()[0]` parses to a major version less than 14, when `is_accessible()` is called, then it returns `False`.

**AC1.3 — `is_accessible()` returns False when ical-guy missing**
Given `shutil.which("ical-guy")` returns `None`, when `is_accessible()` is called, then it returns `False` without invoking any subprocess.

**AC1.4 — `is_accessible()` returns False when probe fails**
Given ical-guy is in PATH but `ical-guy calendars --format json` exits non-zero (e.g., Calendar permission denied), when `is_accessible()` is called, then it returns `False`.

**AC1.5 — `is_accessible()` returns True on success**
Given macOS ≥14, ical-guy in PATH, and the probe call exits zero with parseable JSON, when `is_accessible()` is called, then it returns `True`.

**AC1.6 — `get_tomorrow_events()` returns timed events for target date**
Given Apple Calendar is accessible, when `get_tomorrow_events(target_date)` is called, then it returns a list of dicts each with keys `start` (timezone-aware `datetime`), `end` (timezone-aware `datetime`), `title` (str), `description` (str), `location` (str | None).

**AC1.7 — `get_tomorrow_events()` aggregates events from all Apple Calendars**
Given multiple Apple Calendars contain events for `target_date`, when `get_tomorrow_events(target_date)` is called with no exclusions, then events from every Apple Calendar are present in the returned list (no calendar is silently filtered out).

**AC1.8 — `get_tomorrow_events()` excludes named calendars**
Given `exclude_calendars=["US Holidays", "Birthdays"]`, when `get_tomorrow_events(target_date, exclude_calendars)` is called, then no events from the "US Holidays" or "Birthdays" Apple Calendars appear in the result.

**AC1.9 — `get_tomorrow_events()` excludes all-day events**
Given Apple Calendars contain both timed and all-day events on `target_date`, when `get_tomorrow_events(target_date)` is called, then only events with explicit start and end times are returned.

**AC1.10 — `get_tomorrow_events()` returns only events on target date**
Given Apple Calendars contain events spanning multiple dates, when `get_tomorrow_events(target_date)` is called, then only events whose date matches `target_date` are returned.

**AC1.11 — `get_tomorrow_events()` results sorted by start time ascending**
Given multiple events on the target date across multiple Apple Calendars, when `get_tomorrow_events()` is called, then events are sorted by `start` ascending in the returned list.

**AC1.12 — `get_tomorrow_events()` raises on ical-guy error**
Given ical-guy returns a non-zero exit code or unparseable output during the event read, when `get_tomorrow_events()` is called, then a `RuntimeError` is raised with a descriptive message (the caller in `sync_job.py` will catch and fall back).

**AC1.13 — `description` populated from notes field**
Given an Apple Calendar event has a `notes` field, when it is returned by `get_tomorrow_events()`, then the dict's `description` value equals that notes value.

**AC1.14 — `description` is empty string when notes absent**
Given an Apple Calendar event has no `notes` (null in JSON), when it is returned by `get_tomorrow_events()`, then the dict's `description` value is `""`.

**AC1.15 — `parse_config()` extracts `apple_exclude_calendars`**
Given a YAML config with `calendars.apple_exclude_calendars: ["US Holidays"]`, when `parse_config(raw)` is called, then the returned dict contains `apple_exclude_calendars = ["US Holidays"]`.

**AC1.16 — `parse_config()` returns empty list for missing key**
Given a YAML config with no `apple_exclude_calendars` key, when `parse_config(raw)` is called, then the returned dict has `apple_exclude_calendars = []`.

**AC1.17 — Inaccessible callers receive RuntimeError, not events**
Given `is_accessible()` returns `False` (non-macOS, version too old, ical-guy missing, or permission denied), when `get_tomorrow_events()` is called, then it raises `RuntimeError` with a descriptive reason (`"Apple Calendar not accessible: {reason}"`) — never silently returns events or hangs.

### Implementation Notes

- `is_accessible()`:
  - Short-circuit `False` if `platform.system() != "Darwin"`.
  - Short-circuit `False` if `int(platform.mac_ver()[0].split(".")[0]) < 14` (wrap in try/except — return `False` on parse error).
  - Short-circuit `False` if `shutil.which("ical-guy") is None`.
  - Run `subprocess.run(["ical-guy", "calendars", "--format", "json"], capture_output=True, text=True, timeout=15)`. Return `True` iff `returncode == 0` and `json.loads(stdout)` succeeds.
  - Catch all exceptions; return `False`.

- `get_tomorrow_events(target_date, exclude_calendars=None)`:
  - Re-check `is_accessible()` first; raise `RuntimeError("Apple Calendar not accessible: ical-guy unavailable")` if false.
  - Format date as `target_date.isoformat()` (e.g., `"2026-05-18"`).
  - Build args: `["ical-guy", "events", "--from", date_iso, "--to", date_iso, "--exclude-all-day", "--format", "json"]`. If `exclude_calendars`: append `["--exclude-calendars", ",".join(exclude_calendars)]`.
  - Run with `capture_output=True, text=True, timeout=15`.
  - On non-zero exit: raise `RuntimeError(f"ical-guy events failed: {stderr.strip()}")`.
  - Parse `json.loads(stdout)`. Each event object has `id`, `title`, `startDate` (ISO 8601), `endDate` (ISO 8601), `location` (nullable), `notes` (nullable), `isAllDay` (bool).
  - Filter: skip events where `isAllDay` is true (belt-and-braces; `--exclude-all-day` should already handle this).
  - Filter: skip events whose `startDate` date portion ≠ `target_date.isoformat()` (defensive — ical-guy date ranges may include adjacent-day events depending on timezone).
  - Convert to canonical shape: `{"start": datetime.fromisoformat(startDate), "end": datetime.fromisoformat(endDate), "title": title or "Untitled", "description": notes or "", "location": location}`.
  - Return list sorted by `start` ascending.

- `parse_config()`:
  - Read `data.get("calendars", {}).get("apple_exclude_calendars", [])`.
  - Coerce to list; ignore non-list values (return `[]`).
  - Add `"apple_exclude_calendars"` key to the returned dict.

- Add `_DEFAULTS["apple_exclude_calendars"] = []` to `drive_config.py` if a `_DEFAULTS` dict is used (consistent with existing keys).

- All `subprocess.run()` calls: explicit `timeout=15`, `capture_output=True`, `text=True`.

### Files
- `phantom-calendar/apple_calendar.py` — **new**
- `phantom-calendar/drive_config.py` — extend `parse_config()` (add `apple_exclude_calendars` key)
- `phantom-calendar/tests/test_apple_calendar.py` — **new** (mock `subprocess.run`, `shutil.which`, `platform.system`, `platform.mac_ver`)
- `phantom-calendar/tests/test_drive_config.py` — extend with tests for `apple_exclude_calendars` parsing

---

## US-2 — `sync_job.py`: route reads through Apple Calendar when available

### Description
Modify `run_nightly_sync()` to use `apple_calendar.get_tomorrow_events()` as the event read source when `apple_calendar.is_accessible()` returns `True`. The unified Apple event pool is passed to `compute_alarm()` as the `msi_blocks` argument with `personal_events=[]`. When Apple Calendar is unavailable, behavior is identical to pre-NPC-0014. On any `apple_calendar.*` runtime failure mid-run, a `rumps.notification` is fired with the specific reason and the run falls back to Google Calendar reads. The alarm write path (`run_calendar_write()`) is unchanged.

### Acceptance Criteria

**AC2.1 — Apple reads selected when accessible**
Given `apple_calendar.is_accessible()` returns `True`, when `run_nightly_sync()` starts, then `apple_calendar.get_tomorrow_events(target_date, config["apple_exclude_calendars"])` is called and its result is used as the event source for compute; `get_msi_time_blocks()` and `get_personal_events()` are not called.

**AC2.2 — Google reads when ical-guy not accessible (silent)**
Given `apple_calendar.is_accessible()` returns `False` because ical-guy is not installed or macOS version is unsupported, when `run_nightly_sync()` starts, then `get_msi_time_blocks()` and `get_personal_events()` are called (existing behavior) and no notification is shown.

**AC2.3 — Google reads when Calendar permission denied (silent)**
Given `apple_calendar.is_accessible()` returns `False` because the probe call exited non-zero, when `run_nightly_sync()` starts, then Google Calendar reads are used and no notification is shown.

**AC2.4 — Apple read runtime failure → Google fallback with notification**
Given `apple_calendar.is_accessible()` initially returns `True` but `apple_calendar.get_tomorrow_events()` raises `RuntimeError` during the read, when the exception is caught, then `rumps.notification("Phantom Calendar", "", msg)` is called with `msg` containing the specific error reason, and the pipeline continues with Google Calendar reads (`get_msi_time_blocks()` + `get_personal_events()`).

**AC2.5 — Alarm filter applied to unified pool**
Given the Apple read source returns events that include events with "Alarm" in the title (because Google Calendar alarms are synced into Calendar.app on this machine), when the events are passed to `compute_alarm()`, then events whose title contains `"Alarm"` are filtered out before compute receives them — matching the existing filter applied to `personal_events` in the Google path.

**AC2.6 — Unified pool passed as `msi_blocks` to compute**
Given Apple reads are active, when `compute_alarm()` is called, then it receives the unified Apple event list as `msi_blocks` and an empty list `[]` as `personal_events`.

**AC2.7 — Alarm write path unchanged**
Given any sync run completes (Apple reads or Google reads), when alarm writes occur, then `run_calendar_write(popup_response, config, ...)` is called exactly as before — writing alarms to Google Calendar.

**AC2.8 — macOS detection: Apple reads not attempted on non-macOS**
Given `platform.system() != "Darwin"`, when `run_nightly_sync()` starts, then `apple_calendar.is_accessible()` is called and returns `False`, and the Google Calendar read path is used directly.

**AC2.9 — Google-only behavior preserved when Apple Calendar inaccessible**
Given `apple_calendar.is_accessible()` returns `False`, when `run_nightly_sync()` runs end-to-end, then the observable behavior (events read, alarms computed, alarms written, popup shown) is identical to pre-NPC-0014 behavior.

**AC2.10 — Apple Calendar event data not written to state files**
Given a sync run completes using Apple Calendar reads, when `.phantom_state.json` and any other persistent state file are inspected, then they contain no Apple Calendar event titles, descriptions, or times beyond what the existing state schema already records (e.g., last alarm time — internal data unrelated to event source).

**AC2.11 — Debug logging respects the chosen source**
Given `target_date` is passed to `run_nightly_sync()` (debug/triage mode), when Apple reads are active, then debug output indicates that events came from Apple Calendar (e.g., `[DEBUG] Read source: Apple Calendar`). When Google reads are active, existing debug output is unchanged.

### Implementation Notes

- Add a small helper at the top of `run_nightly_sync()` after `parse_config()`:

  ```python
  use_apple = apple_calendar.is_accessible()
  ```

- Replace the existing read block:

  ```python
  msi_blocks = get_msi_time_blocks(target_date=target_date)
  personal_events = get_personal_events(target_date=target_date)
  ```

  with branching:

  ```python
  if use_apple:
      try:
          unified = apple_calendar.get_tomorrow_events(
              target_date or (date.today() + timedelta(days=1)),
              config.get("apple_exclude_calendars", []),
          )
          # Filter out alarm events synced from Google Calendar
          unified = [e for e in unified if "Alarm" not in e.get("title", "")]
          msi_blocks = unified
          personal_events = []
      except Exception as exc:
          rumps.notification(
              "Phantom Calendar", "",
              f"Apple Calendar read failed: {exc} — using Google Calendar"
          )
          print(f"[sync_job] Apple read failed, falling back: {exc}", file=sys.stderr)
          use_apple = False
          msi_blocks = get_msi_time_blocks(target_date=target_date)
          personal_events = get_personal_events(target_date=target_date)
  else:
      msi_blocks = get_msi_time_blocks(target_date=target_date)
      personal_events = get_personal_events(target_date=target_date)
  ```

- After this block, the rest of the pipeline (`compute_alarm(msi_blocks, personal_events, config)`, popup, write) is **unchanged**.

- The line `result["personal_events"] = [e for e in personal_events if "Alarm" not in e.get("title", "")]` should also remain. With Apple reads it operates on `[]` (no-op); with Google reads it operates as before.

- Debug print at top of try-block (if `debug`): `print(f"[DEBUG] Read source: {'Apple Calendar' if use_apple else 'Google Calendar'}")`.

- Imports: add `import apple_calendar` and `from datetime import date, timedelta` at top of `sync_job.py` (timedelta likely already imported; date is needed for `date.today()`).

- Tests: in `test_sync_job.py`, mock `apple_calendar.is_accessible` and `apple_calendar.get_tomorrow_events`. Cover:
  - (a) `is_accessible() == False` → Google path called, no notification
  - (b) `is_accessible() == True` + read succeeds → Apple path, `get_msi_time_blocks` / `get_personal_events` not called
  - (c) `is_accessible() == True` + read raises → notification fired + Google path called as fallback
  - (d) Alarm event in Apple unified pool → filtered out before compute
  - (e) `apple_exclude_calendars` from config is forwarded to `apple_calendar.get_tomorrow_events()`
  - (f) `run_calendar_write` called identically in both Apple and Google paths

### Files
- `phantom-calendar/sync_job.py` — modify `run_nightly_sync()` read block; add `import apple_calendar`
- `phantom-calendar/tests/test_sync_job.py` — extend with Apple read routing tests
- `phantom-calendar/build/manual_tests.md` — add MT-14 entries
- `phantom-calendar/README.md` — list `apple_calendar.py` in Project Structure; document `ical-guy` as optional runtime dependency for the Apple Calendar read source

---

# Feature-Wide Acceptance Criteria

- All 12 ACs from `feature.md` are covered by the two stories above.
- No Apple Calendar event data appears in any persistent state file after a sync.
- The alarm write path remains completely unchanged — `calendar_writer.py` is not edited by this feature.
- When ical-guy is not installed, the system runs end-to-end identically to pre-NPC-0014.

---

# Constraints

- **Do not modify** `calendar_reader.py`, `calendar_writer.py`, or `compute.py` — Google reads and the alarm write pipeline must remain byte-for-byte unchanged.
- **Do not** write to Apple Calendar from any code path — ical-guy is read-only and no AppleScript writes are added.
- No `tkinter` (enforced by `no-tkinter-in-rumps-process` rune).
- No heredoc (`<< EOF`) — fish shell does not support it.
- Use `platform.system() == "Darwin"` for macOS detection (not `sys.platform`).
- Use `shutil.which("ical-guy")` for PATH detection — do not shell out just for the PATH check.
- All `subprocess.run()` calls to `ical-guy` must pass `timeout=15`, `capture_output=True`, `text=True`.
- macOS 14 (Sonoma)+ requirement enforced inside `is_accessible()` — never let the pipeline reach `get_tomorrow_events()` on an unsupported platform.
- Google Calendar config (`personal_id`, `msi_id`, OAuth credentials) remains required for the alarm write path regardless of which read source is used.

---

# Non-Goals

- Writing alarm events to Apple Calendar (ical-guy is read-only; would require AppleScript and is explicitly out of scope per the updated feature.md).
- Differentiating between work and personal Apple Calendars (single unified pool per the updated feature.md).
- Per-Apple-Calendar configuration of prep times, locations, or classification rules.
- CalDAV direct access — only the macOS Calendar.app local database via ical-guy.
- Changes to the classification dialog, osaurus integration, prep time computation, or alarm write logic.
- Preferences UI for `apple_exclude_calendars` (user edits config directly).

---

# Definition of Done

- `apple_calendar.is_accessible()` and `apple_calendar.get_tomorrow_events()` implemented with unit tests covering all branches (non-macOS, old macOS, no ical-guy, permission denied, success, runtime failure, exclusion, alarm filter, sort, date filter).
- `drive_config.parse_config()` returns `apple_exclude_calendars` key (defaults to `[]`).
- `sync_job.run_nightly_sync()` routes through Apple Calendar reads when accessible, falls back to Google reads on failure with notification.
- `calendar_reader.py`, `calendar_writer.py`, `compute.py` not modified.
- All existing tests pass (no regression to Google pipeline or alarm write).
- `build/manual_tests.md` updated with MT-14 entries.
- `README.md` updated: `apple_calendar.py` in Project Structure; `ical-guy` listed as optional runtime dependency.

---

# Manual Tests (MT-14 — to be added to `build/manual_tests.md` in US-2)

- **MT-14.1** — With ical-guy installed and Calendar permission granted: run sync; verify alarm is written to Google Calendar based on Apple Calendar events (compare event list shown in popup against Calendar.app).
- **MT-14.2** — Uninstall ical-guy (`brew uninstall itspriddle/brews/ical-guy`); run sync; verify no notification appears and behavior is identical to pre-NPC-0014.
- **MT-14.3** — With ical-guy installed but Calendar permission revoked (System Settings → Privacy & Security → Calendars): run sync; verify silent fallback to Google reads.
- **MT-14.4** — With `apple_exclude_calendars: ["US Holidays"]` in config: run sync on a date when US Holidays has an event; verify the popup event list does not include the holiday.
- **MT-14.5** — Manually corrupt ical-guy mid-run (e.g., rename binary while sync is running) — verify the runtime failure notification appears and the run completes via Google reads.
- **MT-14.6** — Verify alarm events synced from Google into Calendar.app are NOT included in the popup event list when Apple reads are active.

---

# Parallelization Analysis

| Story | Files touched | Depends on |
|---|---|---|
| US-1 | `apple_calendar.py` (new), `drive_config.py`, `tests/test_apple_calendar.py` (new), `tests/test_drive_config.py` | — |
| US-2 | `sync_job.py`, `tests/test_sync_job.py`, `build/manual_tests.md`, `README.md` | US-1 (`apple_calendar` module must be importable) |

**Serial** — US-2 imports from `apple_calendar.py` produced by US-1. No overlap in file touches.

---

# Proposed Schema Changes

None to existing schema. One new optional YAML key `calendars.apple_exclude_calendars` (list of strings) is added; absence defaults to empty list (no exclusions). `parse_config()` always returns the key.

---

# Proposed Architecture Changes

A new module `apple_calendar.py` is introduced as a macOS-only **read-only** event source. It is parallel to `calendar_reader.py` but reads from Apple Calendar via ical-guy instead of Google Calendar via the OAuth client. `sync_job.py` gains a small branching block at the top of `run_nightly_sync()` to select the read source; the rest of the pipeline is unchanged.

The alarm write path (`calendar_writer.py`) is untouched. Google Calendar remains the sole alarm-write target.

No new classes; all `apple_calendar` functions are module-level.

---

# File Touch List

| File | Story | Action |
|---|---|---|
| `phantom-calendar/apple_calendar.py` | US-1 | **Create** |
| `phantom-calendar/drive_config.py` | US-1 | Extend `parse_config()` — add `apple_exclude_calendars` key |
| `phantom-calendar/tests/test_apple_calendar.py` | US-1 | **Create** |
| `phantom-calendar/tests/test_drive_config.py` | US-1 | Extend — tests for `apple_exclude_calendars` parsing |
| `phantom-calendar/sync_job.py` | US-2 | Add `import apple_calendar`; modify read block in `run_nightly_sync()` |
| `phantom-calendar/tests/test_sync_job.py` | US-2 | Extend — Apple read routing tests |
| `phantom-calendar/build/manual_tests.md` | US-2 | Add MT-14 entries (6 cases) |
| `phantom-calendar/README.md` | US-2 | Add `apple_calendar.py` to Project Structure; list `ical-guy` as optional dep |
