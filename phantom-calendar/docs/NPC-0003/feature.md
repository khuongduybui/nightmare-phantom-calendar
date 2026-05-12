# What the feature is

Writes a one-time alarm event to the Personal Google Calendar based on the confirmed alarm time from the confirmation popup. Replaces any previously written alarm for the same day. Handles the baseline recurring event safely — overrides only the specific day's occurrence without affecting future recurrences.

# Why we need it

The computed alarm time is useless unless it lands in the calendar where Sleep as Android can read it. This feature is the only component that mutates calendar data, so it must be precise about what it touches and what it leaves alone.

# Acceptance Criteria (testable)

**AC1 — Alarm event written**
Given the popup response is confirmed and a valid alarm time is provided, when the writer runs, then a one-time alarm event is created in the Personal Google Calendar at the confirmed alarm time.

**AC2 — Event duration**
Given an alarm event is written, when it appears in the calendar, then it has a fixed duration of 5 minutes.

**AC3 — Event title format**
Given an alarm event is written, when it appears in the calendar, then the title identifies it as an alarm and includes the name of the first meeting it was computed for.

**AC4 — Existing alarm replaced**
Given a non-baseline alarm event written by this system already exists for tomorrow, when the writer runs, then the existing event is deleted and the new event is written in its place.

**AC5 — Baseline single-occurrence override**
Given the baseline recurring alarm event has an occurrence tomorrow, when the writer needs to place an alarm at a different time on that day, then only that day's occurrence of the baseline is overridden with a one-time event — future recurrences of the baseline are not modified or deleted.

**AC6 — Baseline same-time write skipped**
Given the confirmed alarm time equals the baseline occurrence time for tomorrow, when the writer runs, then no new event is written and the baseline occurrence is left untouched.

**AC7 — Write failure surfaced**
Given the Google Calendar API call fails for any reason, when the writer runs, then the error is surfaced to the user with a message indicating the write failed — no silent failure.

**AC8 — Skip response not written**
Given the popup response is skipped, when the writer is invoked, then no calendar event is created or modified.

**AC9 — Written event is identifiable**
Given an alarm event is written, when it exists in the calendar, then it is distinguishable from user-created events and from the baseline recurring event so future runs can find and replace it.

# System Constraints

- Only writes to the Personal Google Calendar
- Must never delete or modify future recurrences of the baseline recurring event
- Requires a valid OAuth token (NPC-0000 must be complete)
- Baseline event ID must be configurable
- Personal calendar ID must be configurable
- The writer is stateless — it identifies existing alarm events by querying the calendar, not by stored state

# Non-goals

- Undo / delete of a written alarm outside of a new sync run
- Writing to any calendar other than the Personal Google Calendar
- Writing reminders, notifications, or attendees to the alarm event
- Scheduling or triggering the write (belongs in NPC-0004)
- Showing any UI (belongs in NPC-0002)

# Interaction Flow

```mermaid
sequenceDiagram
    participant Sync as Nightly Sync
    participant Writer as Calendar Writer
    participant GCal as Personal Google Calendar

    Sync->>Writer: confirmed alarm time + meeting name
    Writer->>GCal: Query tomorrow for existing alarm events
    GCal-->>Writer: Existing events

    alt Existing non-baseline alarm found
        Writer->>GCal: Delete existing alarm event
    end

    alt Alarm time matches baseline occurrence
        Writer-->>Sync: No write needed, baseline unchanged
    else Alarm time differs from baseline
        Writer->>GCal: Override baseline occurrence for tomorrow only
        Writer->>GCal: Write one-time alarm event
        alt API call fails
            Writer-->>Sync: Surface error to user
        else Success
            Writer-->>Sync: Written event ID
        end
    end
