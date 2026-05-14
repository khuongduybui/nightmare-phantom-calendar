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

### New config shape (optional fields on recurring meetings)

```yaml
recurring_meetings:
  - name: Client Onboarding
    start: "10:00"
    end: "11:00"
    days: [Mon, Tue, Wed, Thu, Fri]
    prep_minutes: 30        # used as fallback if location not found
    location: Client HQ     # optional — maps to config["locations"]
    meeting_type: "New client"  # optional — used to get fixed_minutes from meeting_type_prep
    notes: ""

locations:
  Office: 25
  Client HQ: 45
  Home: 0
```

### Prep time resolution algorithm

```
resolve_prep(meeting, config) -> int:
    location = meeting.get("location")
    meeting_type = meeting.get("meeting_type")

    if location:
        travel_minutes = config["locations"].get(location)
        if travel_minutes is None:
            return config["default_prep_minutes"]  # unknown location → default
        # Get fixed_minutes from meeting_type or prep_minutes
        if meeting_type:
            type_val = config["meeting_type_prep"].get(meeting_type, meeting.get("prep_minutes", 0))
        else:
            type_val = meeting.get("prep_minutes", 0)
        # Parse "travel+N" or int
        fixed = _parse_fixed(type_val)
        return travel_minutes + fixed
    else:
        # No location: use prep_minutes as-is (existing behavior)
        return meeting.get("prep_minutes", config["default_prep_minutes"])

_parse_fixed(val) -> int:
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.startswith("travel+"):
        return int(val.split("+")[1])
    return 0
```

### `parse_config()` changes

`drive_config.parse_config()` already preserves `location` and `meeting_type` keys via passthrough (the recurring meeting dict is normalised with `m.get("location")` etc.). Verify that `parse_config` passes through unknown keys on meeting entries without dropping them.

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

- AC1.1: `compute.py` exports `resolve_prep_minutes(meeting: dict, config: dict) -> int` — a pure function implementing the resolution algorithm above.
- AC1.2: When `meeting["location"]` is set and found in `config["locations"]`, `resolve_prep_minutes` returns `travel_minutes + fixed_minutes`.
- AC1.3: When `meeting["location"]` is set but NOT in `config["locations"]`, returns `config["default_prep_minutes"]`.
- AC1.4: When `meeting` has no `location`, returns `meeting.get("prep_minutes", config["default_prep_minutes"])` — existing behavior unchanged.
- AC1.5: `meeting_type_prep` values of `"travel+N"` contribute `N` as `fixed_minutes` (travel part already counted in travel_minutes). Integer values contribute directly.
- AC1.6: `compute_alarm()` calls `resolve_prep_minutes(matched, config)` instead of using `matched["prep_minutes"]` directly when processing MSI blocks.
- AC1.7: `parse_config()` in `drive_config.py` passes through `location` and `meeting_type` keys on recurring meeting entries (they are already included via `m.get(..., "")` — verify and fix if not).
- AC1.8: No `datetime.utcnow()`.

**Test coverage (`tests/test_travel_time.py`):**
- `test_resolve_prep_no_location_returns_prep_minutes` — meeting with no location; assert returns `prep_minutes`.
- `test_resolve_prep_known_location_integer_type` — location found, `meeting_type` maps to int; assert `travel + fixed`.
- `test_resolve_prep_known_location_travel_plus_type` — location found, `meeting_type` maps to `"travel+10"`; assert `travel + 10`.
- `test_resolve_prep_unknown_location_returns_default` — location not in locations dict; assert default.
- `test_resolve_prep_no_meeting_type_uses_prep_minutes` — location found, no meeting_type; assert `travel + prep_minutes`.
- `test_compute_alarm_uses_resolved_prep` — matched meeting with location; assert alarm uses resolved prep, not raw prep_minutes.
- `test_parse_config_preserves_location_field` — YAML with location on meeting; assert `location` key present in parsed meeting dict.

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

---

## Definition of Done

- [ ] `compute.py`: `resolve_prep_minutes()` exported; `compute_alarm()` uses it.
- [ ] `drive_config.py`: `parse_config()` passes through `location` and `meeting_type` on meeting entries.
- [ ] `preferences.py`: locations editor added after core fields save.
- [ ] `config.yaml`: example location entry added.
- [ ] `tests/test_travel_time.py`: ≥ 11 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.

---

## Parallelization Analysis

US-1 and US-2 touch different files (`compute.py`/`drive_config.py` vs `preferences.py`) — can be written in parallel once the config shape is agreed (fixed in this spec).

---

## File Touch List

### Modify
- `compute.py` — add `resolve_prep_minutes()`, update `compute_alarm()`
- `drive_config.py` — ensure `parse_config()` passes `location`, `meeting_type` through
- `preferences.py` — add locations editor after core fields
- `config.yaml` — add example location

### Create
- `tests/test_travel_time.py`
