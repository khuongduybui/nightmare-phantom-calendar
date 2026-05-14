# What the feature is

Resolves travel-time prep values in `meeting_type_prep` and recurring meeting entries to actual minutes, using the `locations` config. When a meeting requires travel (e.g. prep type `"In-person (local)"` → `"travel+10"`), the system looks up the meeting's location in `config["locations"]` to get travel minutes, then computes total prep as `travel_minutes + fixed_minutes`.

# Why we need it

Currently `meeting_type_prep` entries like `"In-person (local)": "travel+10"` are stored as raw strings and never resolved — the system falls back to `default_prep_minutes` when it encounters them. The `locations` config is always empty because nothing writes to it or reads from it. This feature makes location-based prep time functional.

# How it works

## Config structure

`locations` maps location name → travel minutes:
```yaml
locations:
  Office: 25
  Client HQ: 45
  Home: 0
```

Recurring meeting entries can optionally include a `location` field:
```yaml
recurring_meetings:
  - name: Client Onboarding
    start: "10:00"
    end: "11:00"
    days: [Mon, Tue, Wed, Thu, Fri]
    prep_minutes: 0        # ignored when location is set
    location: Client HQ    # → look up in locations → 45 min travel + 30 fixed = 75 min
    meeting_type: "New client"  # optional: used to get the +N fixed part
    notes: ""
```

## Prep time resolution

When computing prep minutes for a meeting:

1. If meeting has `location` field → look up `config["locations"][location]` → `travel_minutes`
2. If meeting has `meeting_type` field → look up `config["meeting_type_prep"][meeting_type]`
   - If value is `int` → `fixed_minutes = value`
   - If value is `"travel+N"` → `fixed_minutes = N`
   - If not found → `fixed_minutes = config["default_prep_minutes"]`
3. `total_prep = travel_minutes + fixed_minutes`
4. If meeting has no `location` → fall back to existing `prep_minutes` field (no change)

## Locations in Preferences

The Preferences window (NPC-0010) should allow adding/editing location entries so the user doesn't need to edit the Drive config YAML directly.

# Acceptance Criteria (testable)

**AC1 — travel+N prep resolved when location matched**
Given a recurring meeting has a `location` field and `config["locations"]` contains that location, when `compute_alarm()` is called, then prep_minutes = `travel_minutes + fixed_minutes`.

**AC2 — travel+N resolved from meeting_type when no location**
Given a meeting has `meeting_type: "In-person (local)"` and no `location` field, and `meeting_type_prep["In-person (local)"]` is `"travel+10"`, then prep = `10` (no travel; fixed part only).

**AC3 — Unknown location falls back to default**
Given a meeting's `location` is not in `config["locations"]`, when alarm is computed, then `default_prep_minutes` is used and the block is flagged as unknown.

**AC4 — Integer prep_minutes unaffected**
Given a meeting has no `location` and `prep_minutes` is a plain integer, when alarm is computed, then the existing behavior is unchanged.

**AC5 — Locations editable in Preferences**
Given the user opens Preferences, when they navigate to a new Locations section, then they can add, edit, and delete location → travel-time mappings, which are saved to the Drive config.

# System Constraints

- `compute.py` handles travel resolution — no changes to `calendar_reader.py` or `calendar_writer.py`
- `config.yaml` and Drive config YAML schema extended with optional `location` and `meeting_type` fields on recurring meeting entries
- `preferences.py` extended with a Locations editor (add/remove key-value pairs via osascript)
- All config values remain in Drive config — no hardcoded locations

# Non-goals

- Google Maps API for live travel time (Future MVP 3+)
- Auto-detecting meeting location from calendar event details (MSI calendar only exposes time blocks)
- Travel time for personal calendar events
