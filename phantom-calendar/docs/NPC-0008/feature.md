# What the feature is

Enhancements to the menu bar app: persist last run state and last alarm time across app restarts so the menu shows accurate status immediately on launch.

# Why we need it

Currently, "Last run: —" and "Alarm: —" always appear on startup because state is held in memory only. If the app is restarted (e.g. after a Mac restart), the user has no idea when the sync last ran or what alarm was set — even if the sync ran successfully before the restart.

# Acceptance Criteria (testable)

**AC1 — State persisted on sync completion**
Given a sync completes (success or error), when the pipeline finishes, then `last_run_time` and `last_alarm_time` are written to a local state file.

**AC2 — State restored on startup**
Given the state file exists, when the app launches, then `_last_run_item` and `_last_alarm_item` are populated from the saved state before the scheduler starts.

**AC3 — State file location**
The state file lives at `phantom-calendar/.phantom_state.json` (alongside `.drive_config_id`). It is excluded from git.

**AC4 — State file schema**
The state file is a JSON object with keys: `last_run_time` (ISO 8601 string or null) and `last_alarm_time` (ISO 8601 string or null).

**AC5 — Corrupt/missing state file handled gracefully**
Given the state file is missing, malformed, or unreadable, when the app starts, then it falls back to the "—" placeholders without crashing.

**AC6 — Error state persisted**
Given the last sync failed, when the app restarts, then the icon shows ⏰❌ immediately (error state is also persisted).

# System Constraints

- State file is local only — never uploaded to Drive
- `app.py` handles load/save; `sync_job.py` triggers save via `app_ref.update_sync_state()`
- No new dependencies — use stdlib `json` module

# Non-goals

- Custom icon design (post-MVP, requires asset creation)
- Preferences / settings window (post-MVP)
- Syncing state across multiple machines
