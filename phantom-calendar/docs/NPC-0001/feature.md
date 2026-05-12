# What the feature is

Reads the user's MSI Work calendar and Personal Google Calendar for tomorrow, loads meeting configuration from Google Drive, matches time blocks to known meetings, and computes the correct alarm time based on the first meeting of the day. Produces a structured result for downstream use.

# Why we need it

The alarm time cannot be determined without knowing what tomorrow's first commitment is and how much prep it requires. This feature is the decision engine — every other feature either feeds it (config) or acts on its output (popup, calendar writer).

# Acceptance Criteria (testable)

**AC1 — Config loaded from Drive**
Given a valid OAuth token exists, when the feature runs, then meeting configuration is read from the Google Drive config file and parsed into structured data including recurring meetings, prep times, and calendar IDs.

**AC2 — Config values are configurable**
Given a config file exists in Google Drive, when the feature parses it, then all default values (calendar IDs, baseline event ID, default prep minutes, recurring meeting definitions) come from the config file, with sane working defaults used only when a value is absent.

**AC3 — MSI time blocks read**
Given the MSI Work calendar is accessible with at least free/busy reader permission, when the feature runs, then all time blocks for tomorrow are retrieved as start/end pairs (titles not required).

**AC4 — Personal events read**
Given the Personal Google Calendar is accessible, when the feature runs, then all events for tomorrow are retrieved with title and start/end times.

**AC5 — Known MSI block matched**
Given an MSI time block whose start time matches a recurring meeting in config within a 5-minute tolerance, when alarm time is computed, then that meeting's configured prep time is used.

**AC6 — Unknown MSI block flagged**
Given an MSI time block that does not match any known recurring meeting, when alarm time is computed, then it is treated with the default prep time from config and flagged as unknown in the result.

**AC7 — Alarm time computed**
Given one or more meetings are found for tomorrow, when the feature runs, then the alarm time equals the start time of the earliest meeting minus its associated prep time.

**AC8 — No meetings case**
Given both calendars return no events for tomorrow, when the feature runs, then the result indicates no alarm is needed and no error is raised.

**AC9 — Existing alarm events excluded**
Given the Personal calendar contains an alarm event previously written by this system, when personal events are read, then that event is not treated as a meeting and does not influence the computed alarm time.

**AC10 — Result is structured**
Given computation completes, when the result is returned, then it includes: first meeting name, first meeting time, prep minutes used, computed alarm time, whether it matches the baseline, a list of all meetings considered, and a list of unknown MSI blocks.

# System Constraints

- Requires a valid OAuth token (NPC-0000 must be complete)
- MSI calendar access is free/busy reader only — meeting titles are not available
- Config is read from a specific Google Drive file; its ID must be configurable
- Timezone for all time calculations is the user's local timezone, configurable with a working default
- Tomorrow is always the next calendar day regardless of day of week

# Non-goals

- Writing anything to any calendar (belongs in NPC-0003)
- Showing any UI or popup (belongs in NPC-0002)
- Scheduling or triggering this computation at a set time (belongs in NPC-0003)
- Live travel time via Maps API
- Handling multi-day events or all-day events

# Interaction Flow

```mermaid
sequenceDiagram
    participant Caller
    participant Config as Drive Config
    participant MSI as MSI Calendar
    participant Personal as Personal Calendar
    participant Compute

    Caller->>Config: Read config file
    Config-->>Caller: Raw config text
    Caller->>Caller: Parse config
    Caller->>MSI: Fetch tomorrow's time blocks
    MSI-->>Caller: List of start/end pairs
    Caller->>Personal: Fetch tomorrow's events
    Personal-->>Caller: List of events with titles
    Caller->>Compute: Match blocks + compute alarm
    Compute-->>Caller: Structured result
