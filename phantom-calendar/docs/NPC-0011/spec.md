---
spec_hash: ''
---

# NPC-0011 Spec — Location-Based Travel Time

## Clarifications from Codebase

### Current state

- `config["locations"]` is always `{}` — nothing reads or writes it.
- `config["meeting_type_prep"]` contains `"travel+N"` strings that are never resolved.
- `compute.py` uses `matched["prep_minutes"]` directly from recurring meeting config — integer only.
- Recurring meeting entries have `name`, `start`, `end`, `days`, `prep_minutes`, `notes` — no `location` or `meeting_type`.
- `calendar_reader.get_personal_events()` currently returns `{"title", "start", "end"}` — does NOT read the `location` field from the event.

### Location source by calendar type

| Calendar | Location source | Fallback |
|---|---|---|
| **MSI (work)** | Unknown (freeBusyReader only — no event details) | Ask user during classification (NPC-0007 flow); stored on recurring meeting entry |
| **Personal** | Google Calendar `location` field on the event | `"Home"` (0 min travel) if absent or not in `config["locations"]` |

### Config additions

`locations` dict (name → travel minutes in minutes) — `"Home"` always defaults to 0:
```yaml
locations:
  Home: 0          # default fallback; always present
  Office: 25
  Client HQ: 45
```

Optional fields on recurring meeting entries (MSI, set during NPC-0007 classification):
```yaml
recurring_meetings:
  - name: Client Onboarding
    start: "10:00"
    end: "11:00"
    days: [Mon, Tue, Wed, Thu, Fri]
    prep_minutes: 30        # used as fallback if location not found
    location: Client HQ     # optional — maps to config["locations"]
    meeting_type: "New client"
    notes: ""
```

### Prep time resolution algorithm

```
resolve_prep(meeting_or_event, config, event_location=None) -> int:
    # event_location: location string from personal calendar API, or None

    # Determine location name
    if event_location is not None:
        # Personal calendar event with explicit location
        location_name = event_location.strip() or "Home"
    else:
        # MSI recurring meeting — use stored location field
        location_name = meeting_or_event.get("location") or None

    if location_name:
        travel_minutes = config["locations"].get(location_name,
                         config["locations"].get("Home", 0))
        meeting_type = meeting_or_event.get("meeting_type")
        if meeting_type:
            type_val = config["meeting_type_prep"].get(meeting_type, 0)
        else:
            type_val = meeting_or_event.get("prep_minutes", 0)
        fixed = _parse_fixed(type_val)
        return travel_minutes + fixed
    else:
        return meeting_or_event.get("prep_minutes",
               config.get("default_prep_minutes", 30))

_parse_fixed(val) -> int:
    if isinstance(val, int): return val
    if isinstance(val, str) and val.startswith("travel+"): return int(val.split("+")[1])
    return 0
```

### Changes to `calendar_reader.get_personal_events()`

Add `location` field to the returned dict:
```python
{"title": str, "start": datetime, "end": datetime | None, "location": str | None}
```
Read from `event.get("location", "")`.

### NPC-0007 classification extension (MSI unknown blocks)

When classifying an unknown MSI block (NPC-0007 flow in `sync_job._classify_unknown_blocks()`), after the user selects a meeting type, ask: **"Where is this meeting?"** with a `choose from list` of existing location names + "Somewhere else (enter name)" + "Home (no travel)". The selected/entered location is stored on the new recurring meeting entry written back to Drive config.

### `parse_config()` additions

- `"Home": 0` is injected into `config["locations"]` as a default if not already present.
- `location` and `meeting_type` fields are passed through on recurring meeting entries.

### Preferences Locations editor

`preferences.py` gains a Locations section: after saving the 5 core fields, offer to edit locations. Show a `choose from list` with existing locations + "Add new" + "Done". Selecting a location offers Edit/Delete. "Add new" asks for name and travel minutes.

---

## Human-Required Steps

None — all ACs automatable.

---

## User Stories

---

### US-1 — Travel Time Resolution in compute.py

**Story:** As the decision engine, I want recurring meetings with a `location` field to have their prep time resolved as `travel_minutes + fixed_minutes`, so the alarm is set correctly for meetings that require commuting.

**Acceptance Criteria:**

- AC1.1: `compute.py` exports `resolve_prep_minutes(meeting: dict, config: dict, event_location: str | None = None) -> int` — pure function implementing the resolution algorithm.
- AC1.2: When `event_location` is provided (non-empty string), it is used as the location name; empty string falls back to `"Home"`.
- AC1.3: When `event_location` is None and `meeting["location"]` is set and found in `config["locations"]`, returns `travel_minutes + fixed_minutes`.
- AC1.4: When location is not found in `config["locations"]`, falls back to `config["locations"].get("Home", 0) + fixed_minutes`.
- AC1.5: When no location at all, returns `meeting.get("prep_minutes", config["default_prep_minutes"])` — existing behavior unchanged.
- AC1.6: `"travel+N"` values contribute `N` as `fixed_minutes`; integer values contribute directly.
- AC1.7: `compute_alarm()` calls `resolve_prep_minutes(matched, config)` for MSI blocks and `resolve_prep_minutes(event_dict, config, event_location=event["location"])` for personal events.
- AC1.8: `calendar_reader.get_personal_events()` returns `location: str | None` field from the Google Calendar event.
- AC1.9: `parse_config()` injects `"Home": 0` into `config["locations"]` if not already present; passes through `location` and `meeting_type` on meeting entries.
- AC1.10: No `datetime.utcnow()`.

**Test coverage (`tests/test_travel_time.py`):**
- `test_resolve_prep_no_location_returns_prep_minutes` — meeting with no location; assert returns `prep_minutes`.
- `test_resolve_prep_known_location_integer_type` — location found, `meeting_type` maps to int; assert `travel + fixed`.
- `test_resolve_prep_known_location_travel_plus_type` — location found, `meeting_type` maps to `"travel+10"`; assert `travel + 10`.
- `test_resolve_prep_unknown_location_falls_back_to_home` — location not in locations dict; assert uses Home (0) + fixed.
- `test_resolve_prep_event_location_empty_string_uses_home` — `event_location=""`; assert Home fallback.
- `test_resolve_prep_event_location_override` — `event_location="Office"`; assert travel from Office.
- `test_compute_alarm_personal_event_uses_location` — personal event with location field; assert resolved prep used.
- `test_calendar_reader_returns_location_field` — mock API event with location; assert `location` in returned dict.
- `test_parse_config_injects_home_location` — YAML with no Home in locations; assert `"Home": 0` injected.
- `test_parse_config_preserves_location_field` — YAML with location on meeting; assert `location` key present.

**Dependencies:** None.

---

### US-2 — Locations Editor in Preferences

**Story:** As a user, I want to add and edit location → travel-time mappings in Preferences so I don't have to edit YAML on Drive directly.

**Acceptance Criteria:**

- AC2.1: After saving the 5 core preference fields, a `choose from list` dialog shows existing location names + "➕ Add new location" + "✓ Done".
- AC2.2: Selecting an existing location shows options: "Edit travel time" / "Delete" / "Cancel".
- AC2.3: "Edit travel time" prompts for a new travel-minutes value (positive integer validation).
- AC2.4: "Delete" removes the location from the dict.
- AC2.5: "➕ Add new location" prompts for location name, then travel minutes (positive integer).
- AC2.6: "✓ Done" exits the locations editor and the full updated config (including locations) is written to Drive.
- AC2.7: If `config["locations"]` is empty, "➕ Add new location" is the only option shown (plus "✓ Done").

**Test coverage (`tests/test_travel_time.py` — `TestLocationsEditor`):**
- `test_locations_editor_done_immediately_returns_locations` — "Done" with no changes; assert locations unchanged.
- `test_locations_editor_add_new_location` — select "Add new", enter name + minutes; assert new entry in result.
- `test_locations_editor_edit_location` — select existing, edit; assert updated value.
- `test_locations_editor_delete_location` — select existing, delete; assert removed.

**Dependencies:** US-1 (config shape), NPC-0010 (`preferences.py` show() pattern).

---

### US-3 — Date Override (Test Mode)

**Story:** As a developer, I want to run the full sync pipeline against a specific date instead of "tomorrow" so I can test travel time and alarm computation against real past or future calendar events without waiting for the next nightly trigger.

**Acceptance Criteria:**

- AC3.1: `calendar_reader.get_tomorrow_range()`, `get_msi_time_blocks()`, and `get_personal_events()` accept an optional `target_date: date | None = None` parameter. When `None`, behavior is unchanged (tomorrow). When provided, uses that date.
- AC3.2: `sync_job.run_nightly_sync(app_ref=None, target_date=None)` accepts the same optional parameter and passes it through to all calendar reader calls.
- AC3.3: `app.py` gains a **"Run for date…"** menu item (below "Run now") that shows an osascript dialog asking for a date in `YYYY-MM-DD` format, then calls `run_nightly_sync(app_ref=self, target_date=parsed_date)` in a daemon thread.
- AC3.4: Invalid date input (wrong format, non-existent date) shows an error dialog and does not start a sync.
- AC3.5: The date override does NOT affect the scheduler trigger — it only applies to the single manually-triggered run.
- AC3.6: `queue_run()` in `sync_job.py` accepts `target_date=None` and passes it through to `run_nightly_sync()`.

**Test coverage (`tests/test_travel_time.py` — `TestDateOverride`):**
- `test_get_tomorrow_range_uses_target_date` — pass a specific date; assert range uses that date, not tomorrow.
- `test_run_nightly_sync_passes_target_date_to_calendar_reader` — mock calendar reader; assert called with target_date.
- `test_invalid_date_format_shows_error` — mock `_osascript`; assert error dialog shown, sync not started.

**Dependencies:** US-1 (calendar_reader changes already included).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `auth.py` not modified.
- **FAC-4**: `config.yaml` updated with example location entry.
- **FAC-5**: `build/tests.sh` passes without modification.

---

## Constraints

- Python 3.14.
- `compute.py` and `drive_config.py` modified (US-1); `preferences.py` modified (US-2).
- Pure function `resolve_prep_minutes` — no side effects, no network calls.
- `parse_config()` must not drop `location`/`meeting_type` fields on meeting entries.

---

## Non-Goals

- Google Maps API for live travel time.
- Auto-detecting meeting location from calendar event details.
- Travel time for personal calendar events or unknown MSI blocks.
- Persisting the test date across restarts (single-run only).

---

## Definition of Done

- [ ] `compute.py`: `resolve_prep_minutes()` exported; `compute_alarm()` uses it.
- [ ] `calendar_reader.py`: `target_date` parameter on range/block/event functions.
- [ ] `drive_config.py`: `parse_config()` passes through `location` and `meeting_type` on meeting entries.
- [ ] `sync_job.py`: `run_nightly_sync(app_ref, target_date)` passes date to calendar reader; `_classify_unknown_blocks()` asks for location.
- [ ] `app.py`: "Run for date…" menu item.
- [ ] `preferences.py`: locations editor added after core fields save.
- [ ] `config.yaml`: example location entry added.
- [ ] `tests/test_travel_time.py`: ≥ 14 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.

---

## Parallelization Analysis

US-1 and US-2 touch different files (`compute.py`/`drive_config.py` vs `preferences.py`) — can be written in parallel once the config shape is agreed (fixed in this spec).

---

## File Touch List

### Modify
- `compute.py` — add `resolve_prep_minutes()`, update `compute_alarm()`
- `calendar_reader.py` — add `location` field to `get_personal_events()`; add `target_date` param to range/block/event functions
- `drive_config.py` — inject `Home: 0`, pass through `location`/`meeting_type` on meetings
- `sync_job.py` — `run_nightly_sync(app_ref, target_date)`, extend `_classify_unknown_blocks()` for location; `queue_run(target_date)`
- `app.py` — add "Run for date…" menu item
- `preferences.py` — add locations editor after core fields
- `config.yaml` — add Home location and example location

### Create
- `tests/test_travel_time.py`
