# Phantom Calendar — Architecture Reference

> For completed and planned features see [changelog.md](changelog.md).
> For deferred and future work see [backlog.md](backlog.md).
> For setup, running the app, and testing see [README.md](../README.md).

---

## Tech Stack

| Library | Version | Purpose |
|---|---|---|
| `rumps` | 0.4.0 | macOS menu bar app framework |
| `google-api-python-client` | 2.126.0 | Google Calendar + Drive REST API |
| `google-auth-oauthlib` | 1.2.0 | Google OAuth 2.0 installed-app flow |
| `google-auth-httplib2` | 0.2.0 | HTTP transport for Google auth |
| `APScheduler` | 3.10.4 | Background cron scheduler (21:00 daily trigger) |
| `pyyaml` | 6.0.2 | Drive config YAML parsing |
| `pytz` | 2024.1 | Timezone-aware datetime arithmetic |
| `openai` | ≥1.0,<3 | OpenAI-compatible client for local osaurus server |
| `tkinter` | stdlib | Preferences window (main-thread only) |

Python: **3.14** (macOS only — `rumps` is AppKit-backed)

---

## Architecture

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | Entry point — calls `get_credentials()`, then starts `PhantomCalendarApp` |
| `auth.py` | Full OAuth lifecycle: first-run browser flow, `token.json` persistence, silent refresh. Exposes `get_calendar_service()` and `get_drive_service()`. Never modified by feature work |
| `drive_config.py` | Reads the YAML config file from Google Drive; self-healing bootstrap writes the default when the file is absent or invalid; `parse_config()` returns a fully-defaulted dict; `write_config()` / `append_recurring_meetings()` / `append_locations()` write back |
| `calendar_reader.py` | `get_msi_time_blocks()` — free/busy blocks only (freeBusyReader permission); `get_personal_events()` — full events with title, description, location. Both return tz-aware datetimes |
| `compute.py` | `compute_alarm()` — matches MSI blocks to `config["recurring_meetings"]` (5-min tolerance), resolves prep times via `resolve_prep_minutes()` (handles `"travel+N"` strings), collects `unknown_blocks` and `unknown_personal_locations`, returns a structured 9-key result dict |
| `osaurus_client.py` | `suggest_meeting_type(title, description, categories)` — one call to the local osaurus OpenAI-compatible server; validates response against categories; returns `None` on any failure. Never retries. API key read from `osaurus.yaml` |
| `sync_job.py` | `run_nightly_sync(app_ref)` — the full pipeline behind a `threading.Lock`; `queue_run()` queues one pending run via `threading.Event`; `_show_popup()` / `_classify_unknown_blocks()` / `_classify_personal_events()` / `_prompt_unknown_locations()` handle the interactive osascript dialogs |
| `scheduler.py` | `start_scheduler(timezone_str, trigger_time)` — APScheduler `BackgroundScheduler` with a daily `CronTrigger`; `check_and_run_missed_sync()` fires once at startup if 9 PM has already passed |
| `calendar_writer.py` | `run_calendar_write()` — delete stale alarm, write new alarm (tagged `ALARM_TAG = "phantom-calendar-alarm"`), override only tomorrow's baseline occurrence via `events().instances()` + `events().update()`. Never touches future recurrences |
| `app.py` | `PhantomCalendarApp(rumps.App)` — menu bar host; state fields (`_last_run_time`, `_last_alarm_time`, `_last_sync_failed`); `_save_state()` / `_load_state()` to `.phantom_state.json`; `set_syncing()` / `update_sync_state()` drive icon swaps; `show_preferences()` / `_restart_scheduler()` for live preference changes |
| `preferences.py` | `PreferencesWindow(config).show()` — tkinter window (safe on main thread via rumps callback); edits 5 Drive config fields; validates before save; returns updated dict or `None` |

### Data Flow (nightly sync)

```
app.py (9 PM trigger or "Run now")
  └── sync_job.queue_run(app_ref)
        └── run_nightly_sync(app_ref)
              ├── drive_config.read_config() + parse_config()
              ├── calendar_reader.get_msi_time_blocks()
              ├── calendar_reader.get_personal_events()
              ├── compute.compute_alarm(blocks, events, config)
              └── _show_popup(result, config)
                    ├── _classify_unknown_blocks()   [osaurus → choose from list → Recurring/One-shot]
                    ├── _prompt_unknown_locations()  [osascript travel-time input]
                    ├── _classify_personal_events()  [osaurus → choose from list → Recurring/One-shot]
                    └── main confirmation dialog
                          └── calendar_writer.run_calendar_write(response, config, ...)
                                ├── drive_config.append_recurring_meetings()  [if Recurring classifications]
                                └── drive_config.append_locations()           [if new locations]
```

### Key Design Decisions

**Config lives on Google Drive, not locally.**
`config.yaml` in the repo is only the committed default. The live config is the Drive file; `drive_config.py` writes the default there on first run and reads it fresh on every sync. This means config edits from the Preferences window or classification dialogs take effect without touching the local file.

**`auth.py` is never modified by feature work.**
All Google API access goes through `get_calendar_service()` / `get_drive_service()`. OAuth scope changes require re-deleting `token.json`.

**osascript for interactive dialogs; tkinter only on main thread.**
`sync_job.py` runs on a background daemon thread, so it uses `osascript` subprocess calls for all dialogs (blocking the thread is fine there). `preferences.py` uses tkinter because the Preferences menu callback fires on the main thread (rumps routes all menu callbacks to main).

**Alarm events are identified by a tag, not by stored state.**
`ALARM_TAG = "phantom-calendar-alarm"` is written into the event `description`. Each sync queries for this tag to find and delete stale alarms. The writer is stateless — no local DB.

**Baseline recurring event is overridden per-occurrence, never deleted.**
`events().instances()` finds tomorrow's occurrence; `events().update()` patches only that instance. Future recurrences of the baseline are never touched.

**Concurrency: one lock + one queue.**
`_SYNC_LOCK` prevents concurrent pipeline runs. `_PENDING_RUN` (a `threading.Event`) queues at most one follow-up. Both live in `sync_job.py` as module-level globals.

**State persistence is local-only.**
`.phantom_state.json` (excluded from git) stores `last_run_time`, `last_alarm_time`, `last_sync_failed` between app restarts. It is never uploaded anywhere.

**osaurus is always optional.**
`osaurus_client.suggest_meeting_type()` catches all exceptions and returns `None`. The classification dialog always opens — with or without a pre-selection. A stopped osaurus server is invisible to the user.

### Cross-Cutting Invariants

- **Python 3.14** — no `datetime.utcnow()` anywhere; all datetimes are tz-aware
- **`BASE_DIR`** — all file paths are resolved relative to `os.path.dirname(os.path.abspath(__file__))`, never hardcoded absolute paths
- **Fish shell + uv** — `uv run` / `uv pip install`; no bare `python` or `pip` commands in tooling
- **No tkinter from a background thread** — only `preferences.py` (main thread via menu callback) uses tkinter; all other dialogs use osascript
- **`credentials.json`, `token.json`, `.phantom_state.json`, `osaurus.yaml`** excluded from git
- **API key and event data never logged** — `osaurus_client.py` logs only the exception class name to stderr on failure
