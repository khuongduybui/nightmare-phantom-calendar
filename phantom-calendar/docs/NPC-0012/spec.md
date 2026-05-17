---
spec_hash: '75972f8a557d'
---

# NPC-0012 Spec — Unknown Personal-Event Location Prompting

## Clarifications from Codebase

| Feature Term | Codebase Reality |
|---|---|
| "unknown location" | `event["location"]` is non-empty, is not `"Home"`, and is not a key in `config["locations"]` |
| "personal event" | Any event from `get_personal_events()` — processed in `compute_alarm()` via `resolve_prep_minutes(..., event_location=...)` |
| "silent fallback" | `resolve_prep_minutes` falls back to `locations.get("Home", 0)` (= 0) with no flag or log |
| "result dict" | Return value of `compute_alarm()` — currently 7 keys; NPC-0012 adds `unknown_personal_locations` (8th key) |
| "popup" | `_show_popup()` in `sync_job.py` — osascript-based, already loops for `unknown_blocks` via `_classify_unknown_blocks()` |
| "config write for classifications" | `drive_config.append_recurring_meetings()` — serialises full config YAML incl. `locations`; NPC-0012 adds a parallel `append_locations()` |
| Analogous pattern | `unknown_blocks` / `_classify_unknown_blocks()` in `sync_job.py` — NPC-0012 mirrors this for personal event locations |

### `unknown_personal_locations` entry shape

```python
{
    "title": str,           # event["title"]
    "start_time": str,      # event["start"].isoformat()
    "location": str,        # event["location"] (raw string from calendar API)
}
```

### `location_travel_minutes` response key shape

```python
{
    "200 N Nelson Dr, Fountain Inn SC 29644": 45,
    # … one entry per location where user supplied a non-zero value
}
```

---

## User Stories

### US-1 — Detect Unknown Personal-Event Locations in `compute_alarm()`

**Goal:** `compute_alarm()` collects every personal event whose location is non-empty, non-Home, and absent from `config["locations"]`, and returns them as `unknown_personal_locations` in the result dict.

**Files touched:** `compute.py`, `tests/test_compute.py`

#### Acceptance Criteria

| ID | Feature AC | Criterion |
|---|---|---|
| 1.1 | AC1 | When `compute_alarm()` processes a personal event whose `event["location"]` is non-empty, not `"Home"`, and not a key in `config["locations"]`, the result contains `unknown_personal_locations` with one entry for that event including `title`, `start_time` (ISO 8601), and `location`. |
| 1.2 | AC1 | When a personal event's `event["location"]` IS a key in `config["locations"]`, it does NOT appear in `unknown_personal_locations`. |
| 1.3 | AC1, AC7 | When a personal event has no location (`None` or empty string), it does NOT appear in `unknown_personal_locations`. |
| 1.4 | AC1, AC7 | When a personal event has `event["location"] == "Home"`, it does NOT appear in `unknown_personal_locations`. |
| 1.5 | — | Two personal events with the same location string produce two entries in `unknown_personal_locations` (one per event, not deduplicated — each has its own title and start time). |
| 1.6 | — | `resolve_prep_minutes` public signature is unchanged. Detection logic is in `compute_alarm()`. |
| 1.7 | — | `result["unknown_personal_locations"]` is always present (empty list when no unknowns). |
| 1.8 | — | Debug mode prints unknown personal locations: `[DEBUG] Personal '{title}' @ {location} → unknown location (prep=0 min)`. |
| 1.9 | — | Existing `unknown_blocks` key is unaffected. All prior `compute_alarm()` tests pass unchanged. |
| 1.10 | — | Unit tests in `tests/test_compute.py` cover 1.1–1.5. |

**Implementation notes:**
- In `compute_alarm()`, after calling `resolve_prep_minutes(event, config, event_location=event_loc)`, check: if `event_loc` is non-empty, not `"Home"`, and not in `config.get("locations", {})` → append to `unknown_personal_locations` list.
- Accumulate entries in order of encounter (already sorted by time because candidates loop is time-sorted later; no need to pre-sort here).
- Add `unknown_personal_locations` to the return dict alongside `unknown_blocks`.

---

### US-2 — Surface Unknown Locations in Popup and Write to Drive Config

**Depends on:** US-1

**Goal:** `sync_job.py` reads `unknown_personal_locations` from the compute result, prompts the user for travel minutes per location via osascript, recalculates the alarm if affected, returns `location_travel_minutes` in the popup response, and writes non-zero mappings to `config["locations"]` in the Drive config.

**Files touched:** `sync_job.py`, `drive_config.py`, `tests/test_sync_job.py`

#### Acceptance Criteria

| ID | Feature AC | Criterion |
|---|---|---|
| 2.1 | AC2 | When `result["unknown_personal_locations"]` is non-empty and the result is not baseline, `_show_popup()` calls `_prompt_unknown_locations()` before showing the main alarm dialog. |
| 2.2 | AC2 | `_prompt_unknown_locations()` shows one osascript dialog per unique location (grouping events that share the same location string). Each dialog displays the event title(s) and location string, and prompts for an integer travel-minutes value (default `"0"`). |
| 2.3 | AC3 | After each entry, the in-progress `alarm_time` is recalculated: if the event is the first meeting (earliest start), `alarm_time = event["start"] - timedelta(minutes=entered_travel + existing_fixed)`. The recalculated alarm is reflected in the main confirmation dialog. |
| 2.4 | AC4 | `_prompt_unknown_locations()` returns a `location_travel_minutes` dict containing only entries where the user supplied a non-zero integer value. Zero or non-integer input → entry excluded. |
| 2.5 | AC4 | `_show_popup()` merges `location_travel_minutes` into its return dict: `{"confirmed": ..., "alarm_time": ..., "skipped": ..., "classifications": ..., "location_travel_minutes": {...}}`. |
| 2.6 | AC5 | In `run_nightly_sync()`, after the existing `append_recurring_meetings` block, if `popup_response.get("location_travel_minutes")` is non-empty, `append_locations()` is called with those mappings and `config`. |
| 2.7 | AC5 | `drive_config.append_locations(location_travel_minutes: dict, config: dict)` merges new entries into `config["locations"]` and calls `write_config(yaml.dump(...))` with the full config — using the same serialisation pattern as `append_recurring_meetings`. Existing locations are not overwritten. |
| 2.8 | AC6 | The `append_locations()` call is wrapped in a `try/except`; failure logs to stderr and does not affect the alarm event write. |
| 2.9 | AC7 | When `result["unknown_personal_locations"] == []`, `_prompt_unknown_locations()` is not called and `location_travel_minutes` is `{}` in the response. |
| 2.10 | AC8 | When the user enters `0` or leaves the input blank, the location is not added to `location_travel_minutes`. |
| 2.11 | — | osascript dialog cancellation (rc != 0 or user force-quits) is treated as input = 0 for that location (no crash, no write). |
| 2.12 | — | `_show_popup()` always returns `location_travel_minutes` key (empty dict if no unknowns or all zeroes). |
| 2.13 | — | Unit tests in `tests/test_sync_job.py` mock `_osascript` and `drive_config.append_locations` to cover 2.4–2.11. |

**Implementation notes:**
- `_prompt_unknown_locations` signature:
  ```python
  def _prompt_unknown_locations(
      unknown_locs: list, config: dict, current_alarm: "datetime | None"
  ) -> "tuple[dict, datetime | None]":
      # Returns (location_travel_minutes, updated_alarm_time)
  ```
- Group by `location` string: gather all entries with the same location, show them together in one dialog (list the event titles in the prompt text).
- For alarm recalculation: look up the event in `result["all_meetings"]` by matching `start_time`; if its `prep_minutes` is currently 0 (unknown location fallback), add the entered travel minutes and check if it's still the first meeting.
- `append_locations` in `drive_config.py`:
  ```python
  def append_locations(location_travel_minutes: dict, config: dict) -> None:
      updated_locations = {**config.get("locations", {}), **location_travel_minutes}
      # … build updated_data (same shape as append_recurring_meetings) with updated locations …
      write_config(yaml.dump(updated_data, default_flow_style=False, allow_unicode=True))
  ```

---

## Feature-Wide Acceptance Criteria

| ID | Criterion |
|---|---|
| FA-1 | No regression on NPC-0011: personal events whose location IS in `config["locations"]` still resolve correct travel-time prep. |
| FA-2 | No regression on NPC-0007: `result["unknown_blocks"]` is still populated correctly and independently of `unknown_personal_locations`. |
| FA-3 | All existing tests pass without modification. |
| FA-4 | `drive_config.write_config()` → `parse_config()` round-trip preserves new `locations` entries. |

---

## Parallelization Analysis

US-1 and US-2 are strictly sequential: US-2 depends on the `unknown_personal_locations` key shape defined and implemented in US-1. No parallelization.

---

## File Touch List

| File | Story | Change |
|---|---|---|
| `compute.py` | US-1 | Add unknown location detection; add `unknown_personal_locations` to result dict |
| `tests/test_compute.py` | US-1 | Add unit tests for 1.1–1.5 |
| `sync_job.py` | US-2 | Add `_prompt_unknown_locations()`; update `_show_popup()` to call it; add `location_travel_minutes` to response; call `append_locations()` in `run_nightly_sync()` |
| `drive_config.py` | US-2 | Add `append_locations()` function |
| `tests/test_sync_job.py` | US-2 | Add unit tests for 2.4–2.11 |
