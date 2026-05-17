# What the feature is

When the nightly sync popup shows one or more personal calendar events whose location string is not found in `config["locations"]`, the user is prompted to enter travel minutes for each unknown location. The entered value is used to recalculate the alarm time live. The user can optionally save the new location → travel minutes mapping to the Drive config so future events at the same location are resolved automatically.

# Why we need it

Personal events with a street address (e.g. `"200 N Nelson Dr, Fountain Inn SC 29644"`) silently fall back to 0 minutes of travel time because the address is not in `config["locations"]`. The user gets no warning and the alarm is set too late. This feature surfaces the gap at popup time and lets the user correct it — once, with an option to remember it.

# Acceptance Criteria (testable)

**AC1 — Unknown personal-event locations reported in compute result**
Given `compute_alarm()` processes a personal event whose location string is non-empty and not found in `config["locations"]` (and not `"Home"`), when it returns, then the result includes an `unknown_personal_locations` list, where each entry contains the event title, start time, and location string.

**AC2 — Unknown locations shown with travel-time input**
Given the sync result contains one or more unknown personal event locations, when the popup appears, then each entry is shown with the event title, location string, and an input field (defaulting to 0) for travel minutes.

**AC3 — Alarm time recalculates on input**
Given the user enters a travel minutes value for an unknown location, when the value changes, then the displayed alarm time updates immediately if that event is the first meeting.

**AC4 — Location-travel mappings returned in response**
Given the user confirms the popup, when the response is returned, then it includes a `location_travel_minutes` dict mapping each entered location string to the user-supplied travel minutes (only for entries where the user changed the value from 0).

**AC5 — New locations written to Drive config**
Given the popup response includes one or more location-travel mappings, when `run_calendar_write` completes, then each mapping is added to `config["locations"]` in the Drive config file (merge — existing entries unchanged).

**AC6 — Config write is non-fatal**
Given the Drive config update fails for any reason, when the error occurs, then it is logged to stderr and the alarm event write is unaffected.

**AC7 — No prompting when no unknown personal locations**
Given all personal events have no location, a known location, or location `"Home"`, when the popup appears, then no unknown-location section is shown.

**AC8 — Input is optional**
Given an unknown personal location is shown, when the user leaves the travel minutes input at 0, then that location is not written to the Drive config.

# System Constraints

- Unknown location detection happens in `compute_alarm()` and is surfaced via the result dict (new `unknown_personal_locations` key)
- Popup UI is osascript-based (consistent with NPC-0007)
- Drive config write reuses `drive_config.write_config()` and `parse_config()`
- Only personal calendar events with a non-empty, non-Home, unrecognised location string are surfaced — MSI events are handled by NPC-0007
- At most one entry per unique location string per sync run

# Non-goals

- Retroactively updating past alarm times based on newly saved locations
- Editing or deleting existing `config["locations"]` entries (Preferences window — NPC-0010)
- Google Maps API for automatic travel time lookup
- Prompting for MSI block locations (handled by NPC-0007)
