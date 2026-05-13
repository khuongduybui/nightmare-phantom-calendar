# What the feature is

When the nightly sync popup shows one or more unknown MSI calendar blocks, the user can classify each block by meeting type. Selecting a type recalculates the alarm time live based on that type's configured prep time. The classification is returned in the sync response and written back to `config['recurring_meetings']` in the Drive config file so the meeting is recognized automatically on future runs.

# Why we need it

Unknown MSI blocks default to 30 minutes of prep time, which is often wrong. When a new recurring meeting is added to the work calendar, the app treats it as unknown indefinitely unless the user manually edits the config. This feature closes that loop: the user classifies it once and the app learns it.

# Acceptance Criteria (testable)

**AC1 — Unknown blocks shown with classification UI**
Given the sync result contains one or more unknown MSI blocks, when the popup appears, then each unknown block is shown with its start time and a dropdown/selector of meeting types from `config['meeting_type_prep']`.

**AC2 — Alarm time recalculates on selection**
Given the user selects a meeting type for an unknown block, when the selection changes, then the displayed alarm time updates immediately based on the selected type's prep time and the block's start time.

**AC3 — Classification returned in response**
Given the user confirms the popup, when the response is returned, then it includes a `classifications` list mapping each unknown block's start time to the selected meeting type name.

**AC4 — New recurring meeting written to Drive config**
Given the popup response includes one or more classifications, when run_calendar_write completes, then each classified block is appended as a new entry to `config['recurring_meetings']` in the Drive config file, using the block's start time and the selected meeting type's prep time.

**AC5 — No classification on baseline or no-meetings**
Given the result is a baseline match or has no meetings, when the popup appears, then no classification UI is shown.

**AC6 — Classification optional**
Given an unknown block is present, when the user leaves the dropdown at the default (e.g. "Unknown — 30 min"), then no new recurring meeting is written to the Drive config for that block.

**AC7 — Config write is non-fatal**
Given the Drive config update fails for any reason, when the error occurs, then it is logged to stderr and the alarm event write is unaffected — the user still gets their alarm.

# System Constraints

- Classification UI is within the osascript dialog (NPC-0006 replaced tkinter with osascript)
- `config['meeting_type_prep']` provides the list of types and their prep times
- The Drive config write reuses `drive_config.write_config()` and `parse_config()`
- Only unknown MSI blocks are classified — personal events are not
- At most one classification per block per sync run

# Non-goals

- Retroactively classifying past unknown blocks
- Editing or deleting existing recurring meeting entries
- UI for managing the full recurring meetings list
- Classification of personal calendar events
