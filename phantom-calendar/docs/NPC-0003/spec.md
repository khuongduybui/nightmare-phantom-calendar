---
spec_hash: ''
---

# NPC-0003 Spec — Calendar Writer

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "popup response" | `{"confirmed": bool, "alarm_time": datetime\|None, "skipped": bool}` | `popup.py::ConfirmationPopup.show()` |
| "confirmed alarm time" | `popup_response["alarm_time"]` (tz-aware datetime) | `popup.py` |
| "meeting name" | `compute_result["first_meeting_name"]` passed in via caller | caller's responsibility |
| "Personal Google Calendar" | `config["personal_calendar_id"]` | `drive_config.parse_config()` |
| "baseline recurring event" | `config["baseline_event_id"]` | `drive_config.parse_config()` |
| "system-written alarm events" | events with `"phantom-calendar-alarm"` in `description` | `calendar_writer.py::ALARM_TAG` |
| "identify existing alarm" | `events().list(q=ALARM_TAG)` | `calendar_writer.py` |
| "override single occurrence" | `events().instances()` → `events().update()` | `calendar_writer.py` |
| "calendar API service" | `auth.get_calendar_service()` | `auth.py` (existing) |
| "tomorrow" | `date.today() + timedelta(days=1)` in config timezone | `calendar_writer.py` |

### Key Design Decisions

1. **Event identification tag**: `ALARM_TAG = "phantom-calendar-alarm"` is a module-level constant in `calendar_writer.py`. Written events have this string in their `description`. The `get_existing_alarm_for_tomorrow()` query uses `q=ALARM_TAG`.

2. **Alarm event title**: `f"⏰ Alarm — {meeting_name}"` — includes the meeting name for human readability.

3. **Alarm event duration**: 5 minutes (per feature.md AC2). End time = `alarm_time + timedelta(minutes=5)`.

4. **Baseline override approach**:
   - Call `events().instances(calendarId=..., eventId=BASELINE_EVENT_ID, timeMin=..., timeMax=...)` to find tomorrow's occurrence.
   - Call `events().update(calendarId=..., eventId=<instance_id>, body=<modified>)` to override that single occurrence only.
   - Never delete the recurring event. Never touch future occurrences.

5. **Timezone for API calls**: All `timeMin`/`timeMax` strings are ISO 8601 with timezone offset (from `config["timezone"]`), not UTC `Z` suffix — consistent with `calendar_reader.py`.

6. **`meeting_name` source**: The caller (`sync_job.py` in NPC-0004) passes `meeting_name` separately. `run_calendar_write()` signature: `run_calendar_write(popup_response, config, meeting_name)`.

7. **Mismatch with feature.md FR-4**: feature.md says title comes from `config["meeting_name"]`. This key does not exist in `drive_config.parse_config()` output. The correct source is the `compute_alarm()` result's `first_meeting_name`, passed by the caller. Spec: `meeting_name` is a parameter to `run_calendar_write()`.

### Mismatches vs. project.md Step 6

- project.md uses UTC `Z` suffix for timeMin/timeMax — spec uses local tz ISO strings (consistent with existing `calendar_reader.py` pattern).
- project.md event duration is 30 minutes — feature.md says 5 minutes. **Feature.md wins: 5 minutes.**
- project.md `get_tomorrow_window()` uses `datetime.datetime` without timezone — spec uses tz-aware datetimes.

---

## Human-Required Steps

### H-1 — Calendar write permission
`token.json` must include `https://www.googleapis.com/auth/calendar` scope (not just read). Already included in `auth.py::SCOPES`. If existing token lacks write scope, delete `token.json` and re-run `uv run main.py`.

### H-2 — Baseline event ID correct
`config["baseline_event_id"]` must be the correct Google Calendar event ID for the baseline recurring event. Verify it matches the actual recurring event in the Personal calendar.

---

## User Stories

---

### US-1 — Core Write Operations

**Story:** As the nightly sync, I want `calendar_writer.py` to provide functions for querying existing alarm events, deleting them, and writing new alarm events, so that the orchestration layer can manage the alarm state for tomorrow.

**Acceptance Criteria:**

- AC1.1: `ALARM_TAG = "phantom-calendar-alarm"` is a module-level constant.
- AC1.2: `get_tomorrow_range(timezone_str: str) -> tuple[str, str]` returns `(start_iso, end_iso)` covering all of tomorrow in the given timezone, as ISO 8601 strings with timezone offset.
- AC1.3: `get_existing_alarm_for_tomorrow(service, calendar_id: str, timezone_str: str) -> list[dict]` queries `events().list(calendarId=..., timeMin=..., timeMax=..., q=ALARM_TAG, singleEvents=True)` and returns the list of matching event dicts. Returns `[]` when none found.
- AC1.4: `delete_alarm_event(service, calendar_id: str, event_id: str) -> None` calls `events().delete(calendarId=..., eventId=...)`.
- AC1.5: `write_alarm_event(service, calendar_id: str, alarm_time: datetime, meeting_name: str, timezone_str: str) -> dict` creates an event with:
  - `summary`: `f"⏰ Alarm — {meeting_name}"`
  - `description`: `ALARM_TAG`
  - `start.dateTime`: `alarm_time.isoformat()`
  - `start.timeZone`: `timezone_str`
  - `end.dateTime`: `(alarm_time + timedelta(minutes=5)).isoformat()`
  - `end.timeZone`: `timezone_str`
  - Returns the created event dict.
- AC1.6: No `datetime.utcnow()` calls. All datetimes are tz-aware.
- AC1.7: `auth.py` not modified.

**Test coverage (`tests/test_calendar_writer.py` — `TestCoreWriteOps`):**
- `test_get_tomorrow_range_covers_next_day` — assert start/end bracket tomorrow in correct timezone.
- `test_get_existing_alarm_returns_matching_events` — mock service; assert `q=ALARM_TAG` passed; returns items list.
- `test_get_existing_alarm_returns_empty_list_when_none` — mock returns `{"items": []}`; assert `[]`.
- `test_delete_alarm_event_calls_api` — assert `events().delete(calendarId=..., eventId=...)` called.
- `test_write_alarm_event_correct_fields` — assert `summary`, `description`, `start`, `end` fields on inserted event.
- `test_write_alarm_event_duration_5_minutes` — assert end = start + 5 min.

**Dependencies:** None. Uses existing `auth.py`.

---

### US-2 — Baseline Handling + Orchestration

**Story:** As the nightly sync, I want `run_calendar_write()` to orchestrate the full write flow — skipping when appropriate, deleting stale alarms, writing the new alarm, and safely overriding only tomorrow's baseline occurrence — so that the calendar is always in the correct state after a confirmed sync.

**Acceptance Criteria:**

- AC2.1: `get_baseline_instance_for_tomorrow(service, calendar_id: str, baseline_event_id: str, timezone_str: str) -> dict | None` calls `events().instances(calendarId=..., eventId=baseline_event_id, timeMin=..., timeMax=..., maxResults=1)` and returns the first instance dict, or `None` if no instance found.
- AC2.2: `override_baseline_occurrence(service, calendar_id: str, instance: dict, alarm_time: datetime, timezone_str: str) -> dict` updates the instance's `start` and `end` to `alarm_time` / `alarm_time + 5 min` and calls `events().update(calendarId=..., eventId=instance["id"], body=instance)`. Returns the updated event dict.
- AC2.3: `run_calendar_write(popup_response: dict, config: dict, meeting_name: str) -> None`:
  - Returns immediately (no API calls) if `popup_response["skipped"]` is True. (feature.md AC8)
  - Returns immediately (no API calls) if `popup_response["confirmed"]` is False. (feature.md AC8)
  - Otherwise: calls `get_existing_alarm_for_tomorrow()`, deletes each found event, calls `write_alarm_event()`, and if `config.get("baseline_event_id")` is set, calls `get_baseline_instance_for_tomorrow()` and (if instance found) `override_baseline_occurrence()`. (feature.md AC1–AC5)
- AC2.4: `run_calendar_write()` prints a status line for each action (delete, write, override) — not silent. (feature.md AC7 / "surfaced")
- AC2.5: If `events().insert()` or `events().update()` raises an exception, `run_calendar_write()` catches it, prints a human-readable error message, and re-raises so the caller can handle it. (feature.md AC7)
- AC2.6: Baseline event's future recurrences are never deleted or modified — only the specific instance returned by `events().instances()` is updated. (feature.md AC5)
- AC2.7: All calendar IDs and event IDs come from `config` — never hardcoded. (feature.md system constraint)

**Test coverage (`tests/test_calendar_writer.py` — `TestBaselineAndOrchestration`):**
- `test_run_skipped_makes_no_api_calls` — `skipped=True`; assert service not called.
- `test_run_not_confirmed_makes_no_api_calls` — `confirmed=False, skipped=False`; assert service not called.
- `test_run_confirmed_deletes_existing_and_writes_new` — mock existing alarm; assert delete called, then insert called.
- `test_run_confirmed_no_existing_alarm` — mock no existing; assert insert called, delete not called.
- `test_run_overrides_baseline_occurrence_when_present` — mock baseline instance found; assert `events().update()` called with correct instance id.
- `test_run_skips_baseline_override_when_no_instance` — mock `events().instances()` returns empty; assert no update call.
- `test_run_surfaces_write_error` — mock insert raising exception; assert exception re-raised.
- `test_get_baseline_instance_returns_none_when_no_items` — mock returns `{"items": []}`; assert `None`.

**Dependencies:** US-1 (functions used by orchestration).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0 (all tests pass).
- **FAC-2**: `requirements.txt` unchanged — all needed libraries already present.
- **FAC-3**: `credentials.json` and `token.json` absent from committed files.
- **FAC-4**: No `datetime.utcnow()` in any new code.
- **FAC-5**: `auth.py` not modified.
- **FAC-6**: `README.md` updated to add `calendar_writer.py` to Project Structure table.
- **FAC-7**: `build/tests.sh` runs without modification.
- **FAC-8**: `ALARM_TAG` is a single module-level constant — not duplicated across files.

---

## Constraints

- Python 3.14 — no `datetime.utcnow()`.
- Fish shell, uv conventions throughout.
- macOS only at runtime.
- `calendar_writer.py` at project root.
- `auth.py` must not be modified.
- All API calls mocked in unit tests — no live network calls in pytest.
- Baseline event never deleted — only single-occurrence override via `events().update()`.

---

## Non-Goals

- Undo / delete of a written alarm outside of a new sync run.
- Writing to any calendar other than Personal Google Calendar.
- Writing reminders, notifications, or attendees.
- Scheduling or triggering the write (NPC-0004).
- Showing any UI (NPC-0002).

---

## Definition of Done

- [ ] `calendar_writer.py` created: `ALARM_TAG`, `get_tomorrow_range()`, `get_existing_alarm_for_tomorrow()`, `delete_alarm_event()`, `write_alarm_event()`, `get_baseline_instance_for_tomorrow()`, `override_baseline_occurrence()`, `run_calendar_write()`.
- [ ] `tests/test_calendar_writer.py` — ≥ 14 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated with `calendar_writer.py` in Project Structure table.
- [ ] No `credentials.json` / `token.json` in staged files.
- [ ] No `datetime.utcnow()` in new code.
- [ ] `build/tests.sh` passes without modification.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 (core write ops) | None | — |
| US-2 (baseline + orchestration) | US-1 (calls its functions) | Cannot parallelize |

Sequential dependency. US-2 source can be written once US-1 function signatures are fixed (immediately — fixed in this spec).

---

## Proposed Schema Changes

None.

## Proposed Architecture Changes

None. `calendar_writer.py` follows the flat project-root layout.

---

## File Touch List

### Create
```
phantom-calendar/
├── calendar_writer.py
└── tests/
    └── test_calendar_writer.py
```

### Modify
- `README.md` — add `calendar_writer.py` to Project Structure table.

### Do NOT touch
- `auth.py`, `app.py`, `main.py`, `requirements.txt`
- `drive_config.py`, `calendar_reader.py`, `compute.py`, `popup.py`
- `build/tests.sh`, `build/manual_tests.md`
- `tests/smoke_imports.py`, `tests/test_auth.py`, `tests/test_main.py`
- `tests/test_drive_config.py`, `tests/test_calendar_reader.py`, `tests/test_compute.py`, `tests/test_popup.py`
