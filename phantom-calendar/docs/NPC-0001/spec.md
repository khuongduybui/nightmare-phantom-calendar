---
spec_hash: '46a663679694'
---

# NPC-0001 — Decision Engine: Spec

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "Google Drive config file" | `CONFIG_FILE_ID` constant | `drive_config.py` (to create) |
| "config file ID must be configurable" | `os.environ.get('PHANTOM_CONFIG_FILE_ID', '<default>')` | `drive_config.py` |
| "meeting configuration" | `parse_config()` return dict | `drive_config.py` |
| "recurring meetings" | `config['recurring_meetings']` list | `drive_config.py` |
| "default prep minutes" | `config['default_prep_minutes']` (int) | `drive_config.py` |
| "calendar IDs" in config | `config['personal_calendar_id']`, `config['msi_calendar_id']` | `drive_config.py` |
| "baseline event ID" | `config['baseline_event_id']` | `drive_config.py` |
| "MSI Work calendar time blocks" | `get_msi_time_blocks()` → `list[dict]` with `start`, `end` | `calendar_reader.py` |
| "Personal Google Calendar events" | `get_personal_events()` → `list[dict]` with `title`, `start`, `end` | `calendar_reader.py` |
| "tomorrow" | `date.today() + timedelta(days=1)` in `LOCAL_TZ` | `calendar_reader.py` |
| "user's local timezone" | `LOCAL_TZ = pytz.timezone('America/New_York')` | `calendar_reader.py` |
| "alarm event previously written by this system" | personal events where `'Alarm' in event['title']` | `compute.py` |
| "5-minute tolerance" | `abs((block_start - meeting_start).total_seconds()) <= 300` | `compute.py` |
| "unknown MSI block" | unmatched block appended to `result['unknown_blocks']` | `compute.py` |
| "structured result" (AC10) | `compute_alarm()` return dict with 7 keys | `compute.py` |
| "valid OAuth token" | `auth.get_credentials()` / `token.json` | `auth.py` (existing) |
| Drive API service | `auth.get_drive_service()` | `auth.py` (existing) |
| Calendar API service | `auth.get_calendar_service()` | `auth.py` (existing) |

### Config File Format

The Google Drive config file is stored as **YAML** (not markdown). `parse_config()` uses `yaml.safe_load()`. The canonical default is committed as `config.yaml` at the project root and mirrored as `DEFAULT_CONFIG_YAML` in `drive_config.py`. On first pull, if the Drive file is not valid YAML, `bootstrap_config()` writes the default to Drive and renames the file to `config.yaml` if needed.

```yaml
calendars:
  personal_id: duykbui1989@gmail.com
  msi_id: duy.bui@motorolasolutions.com
  daily_run_time: "19:00"

timezone: America/New_York

default_prep_minutes: 30

baseline_event:
  id: l13abvd0p0vkphit24u6bkhuf8
  title: Daily Standup Alarm
  time: "09:25"

recurring_meetings:
  - name: AERSS Standup
    start: "09:30"
    end: "09:45"
    days: [Mon, Tue, Wed, Thu, Fri]
    prep_minutes: 5
    notes: Baseline recurring alarm
  - name: Pod 8 Daily Sync
    start: "12:30"
    end: "12:45"
    days: [Mon, Tue, Wed, Thu, Fri]
    prep_minutes: 15
    notes: Alarm at 12:15 if first meeting of day

meeting_type_prep:
  Daily standup: 5
  Regular online meeting: 10
  New platform (first use): 15
  New client: 30
  Interview: 30
  In-person (local): travel+10
  In-person (far): travel+15
  Unknown: 30

locations: {}

client_overrides: {}
```

Values that involve travel time (`travel+N`) are stored as strings; integer-only values are stored as ints. `parse_config()` returns them as-is — downstream features interpret `travel+N` strings.

### Mismatches Between feature.md and project.md

1. **CONFIG_FILE_ID hardcoded in project.md**: Spec: `os.environ.get('PHANTOM_CONFIG_FILE_ID', '1nPSl33iRhs5Jnv1SxNxdc9qHoID5J1UF')`. (feature.md AC2)

2. **project.md uses pipe-delimited markdown parsing**: Replaced by `yaml.safe_load()`. All values come from YAML — no value is hardcoded without a file override.

3. **Alarm event identification**: `'Alarm' in event['title']` per project.md. Accepted.

4. **`is_baseline` coupling**: `first['name'] == config['baseline_event_title']` (not hardcoded string). Uses value from parsed config.

5. **`datetime.utcnow()` removed in Python 3.14**: Use `datetime.now(tz=...)` throughout.

6. **PyYAML not in requirements.txt**: Must be added. `pyyaml==6.0.2` (latest stable). This is the only requirements change for NPC-0001.

---

## Human-Required Steps

Prerequisites for live API verification only. Unit tests mock all API calls.

### H-1 — Drive scope in token
`token.json` must be authorised for `https://www.googleapis.com/auth/drive.file`. `auth.py::SCOPES` already includes this scope. If the existing token pre-dates Drive scope, delete `token.json` and re-run `uv run main.py`.

### H-2 — MSI calendar freeBusyReader permission
`duy.bui@motorolasolutions.com` must grant the authenticated account at least `freeBusyReader` permission on the calendar.

---

## User Stories

---

### US-1 — Drive Config Module

**Story:** As the decision engine, I can load and parse meeting configuration from Google Drive so that all configurable values come from the config file with sane defaults when absent.

**Acceptance Criteria:**

- AC1.1: `drive_config.py` exists at project root.
- AC1.2: `CONFIG_FILE_ID = os.environ.get('PHANTOM_CONFIG_FILE_ID', '1nPSl33iRhs5Jnv1SxNxdc9qHoID5J1UF')` is a module-level constant. (feature.md AC2)
- AC1.3: `read_config() -> str` calls `auth.get_drive_service()`, executes `files().get_media(fileId=CONFIG_FILE_ID)`, returns content decoded as `str`. (feature.md AC1)
- AC1.4: `parse_config(raw: str) -> dict` returns a dict with these keys and defaults when absent from `raw`:
  - `personal_calendar_id`: `'duykbui1989@gmail.com'`
  - `msi_calendar_id`: `'duy.bui@motorolasolutions.com'`
  - `baseline_event_id`: `'l13abvd0p0vkphit24u6bkhuf8'`
  - `recurring_meetings`: `[]`
  - `default_prep_minutes`: `30`
  - `timezone`: `'America/New_York'`
  (feature.md AC2)
- AC1.5: Each recurring meeting dict has: `name` (str), `start` (str), `end` (str), `days` (list[str]), `prep_minutes` (int).
- AC1.6: `parse_config` skips table header rows (containing `'Logical name'` or `'---'`) and rows with fewer than 4 pipe-delimited fields.
- AC1.7: `parse_config('')` returns full defaults without raising.
- AC1.8: No `datetime.utcnow()` calls.

**Test coverage (`tests/test_drive_config.py`):**
- `test_read_config_returns_valid_yaml_unchanged` — mock Drive returns valid YAML; assert same string returned, `bootstrap_config` not called.
- `test_read_config_invalid_yaml_triggers_bootstrap` — mock Drive returns `'not: valid: yaml: :::'`; assert `bootstrap_config()` called and `DEFAULT_CONFIG_YAML` returned.
- `test_read_config_empty_content_triggers_bootstrap` — mock Drive returns `''`; assert bootstrap triggered.
- `test_read_config_decodes_bytes_response` — mock `execute()` returning bytes of valid YAML; assert str returned.
- `test_bootstrap_config_writes_default_and_renames` — mock `get_drive_service`, mock `files().get(fileId=...).execute()` returning `{'name': 'config'}` (non-yaml name); assert `write_config` called with `DEFAULT_CONFIG_YAML` and rename update called.
- `test_bootstrap_config_skips_rename_if_already_yaml` — mock current filename `config.yaml`; assert rename not called.
- `test_parse_config_all_defaults_on_empty_input` — pass `''`; assert all 12 keys present with correct defaults.
- `test_parse_config_overrides_calendar_ids` — YAML with `calendars.personal_id`; assert `personal_calendar_id` overridden.
- `test_parse_config_parses_recurring_meeting` — YAML with one `recurring_meetings` entry; assert `name` and `prep_minutes` correct.
- `test_parse_config_parses_meeting_type_prep` — YAML with `meeting_type_prep`; assert int and string (`travel+10`) values preserved.
- `test_parse_config_parses_locations_and_overrides` — YAML with `locations` and `client_overrides` entries; assert dicts populated.
- `test_config_file_id_uses_env_var` — patch `PHANTOM_CONFIG_FILE_ID` env var; assert override used in Drive API call.

**Dependencies:** None. Uses existing `auth.py`.

---

### US-2 — Calendar Reader Module

**Story:** As the decision engine, I can fetch tomorrow's MSI time blocks (start/end only) and Personal calendar events (with titles) so I have the raw data needed to compute the alarm time.

**Acceptance Criteria:**

- AC2.1: `calendar_reader.py` exists at project root.
- AC2.2: `PERSONAL_CALENDAR_ID = 'duykbui1989@gmail.com'` and `MSI_CALENDAR_ID = 'duy.bui@motorolasolutions.com'` are module-level constants.
- AC2.3: `LOCAL_TZ = pytz.timezone('America/New_York')` is a module-level constant.
- AC2.4: `get_tomorrow_range() -> tuple[str, str]` returns `(start_iso, end_iso)` covering all of tomorrow in `LOCAL_TZ`. "Tomorrow" = `date.today() + timedelta(days=1)` in local time. (feature.md AC3/AC4)
- AC2.5: `get_msi_time_blocks(calendar_id=MSI_CALENDAR_ID) -> list[dict]` calls `auth.get_calendar_service()`, uses `singleEvents=True, orderBy='startTime'`, returns `[{'start': datetime, 'end': datetime}]` for events with `'dateTime'` key. Events with only `'date'` silently skipped. (feature.md AC3)
- AC2.6: `get_personal_events(calendar_id=PERSONAL_CALENDAR_ID) -> list[dict]` returns `[{'title': str, 'start': datetime, 'end': datetime|None}]` for events with `'dateTime'`. (feature.md AC4)
- AC2.7: Both return `[]` when API returns no events. (feature.md AC8)
- AC2.8: Both return results sorted by `start` ascending.
- AC2.9: `datetime.fromisoformat()` used to parse `dateTime` strings. No `datetime.utcnow()`.

**Test coverage (`tests/test_calendar_reader.py`):**
- `test_get_tomorrow_range_covers_next_day` — freeze today; assert range brackets next calendar day.
- `test_get_msi_time_blocks_returns_start_end_only` — mock API event with `summary` and `dateTime`; result has `start`/`end` only, no `title`.
- `test_get_msi_time_blocks_skips_all_day_events` — event with `date` key only; assert `[]`.
- `test_get_personal_events_includes_title` — event `summary='Stand-up'`; assert `title='Stand-up'` in result.
- `test_get_personal_events_empty_list` — mock `{'items': []}`; assert `[]`.
- `test_get_msi_time_blocks_sorted_ascending` — two out-of-order events; assert sorted by start.

**Dependencies:** None. Uses existing `auth.py`.

---

### US-3 — Compute Module

**Story:** As the decision engine, I can take config, MSI time blocks, and personal events and produce a structured alarm-time result including meeting matching, unknown block flagging, earliest-meeting selection, alarm-event exclusion, and the no-meetings case.

**Acceptance Criteria:**

- AC3.1: `compute.py` exists at project root.
- AC3.2: `match_block_to_meeting(block: dict, recurring_meetings: list) -> dict | None` matches `block['start']` to a recurring meeting within 5 minutes (`abs(delta.total_seconds()) <= 300`). Returns meeting dict or `None`. (feature.md AC5)
- AC3.3: `compute_alarm(msi_blocks: list, personal_events: list, config: dict) -> dict` returns a dict with exactly these 7 keys: `first_meeting_name`, `first_meeting_time`, `prep_minutes`, `alarm_time`, `is_baseline`, `all_meetings`, `unknown_blocks`. (feature.md AC10)
- AC3.4: MSI block matched → use meeting's `prep_minutes`. Unmatched → use `config['default_prep_minutes']`, append to `unknown_blocks`. (feature.md AC5, AC6)
- AC3.5: Personal events with `'Alarm'` in `title` excluded from candidates. (feature.md AC9)
- AC3.6: Remaining personal events added as candidates with `prep_minutes=10`.
- AC3.7: Candidates sorted by start; earliest is `first_meeting_*`. `alarm_time = first_meeting_time - timedelta(minutes=prep_minutes)`. (feature.md AC7)
- AC3.8: No candidates: `first_meeting_name=None`, `first_meeting_time=None`, `prep_minutes=0`, `alarm_time=None`, `is_baseline=True`, `all_meetings=[]`. (feature.md AC8)
- AC3.9: `is_baseline=True` when `alarm_time is None` OR (first meeting name matches `config['baseline_event_title']` and `alarm_time` matches `config['baseline_event_time']`).
- AC3.10: No network calls — pure computation.

**Test coverage (`tests/test_compute.py`):**
- `test_match_within_5_min_returns_meeting` — block 4 min after meeting start; returns meeting dict.
- `test_match_outside_tolerance_returns_none` — block 6 min off; `None`.
- `test_compute_alarm_known_block_uses_meeting_prep` — matched block; meeting's `prep_minutes`, `unknown_blocks=[]`.
- `test_compute_alarm_unknown_block_uses_default_prep` — unmatched; default prep, block in `unknown_blocks`.
- `test_compute_alarm_excludes_alarm_events` — personal event `title='Standup Alarm'`; not in candidates.
- `test_compute_alarm_picks_earliest` — two candidates; earliest is `first_meeting_time`.
- `test_compute_alarm_no_meetings` — empty inputs; `alarm_time=None`, `is_baseline=True`.
- `test_compute_alarm_result_has_all_7_keys` — assert exactly the 7 required keys present.

**Dependencies:** US-1 (config dict shape) and US-2 (msi_blocks/personal_events shapes) must be agreed upon before implementation. Source files can be written in parallel.

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0 (all stories' tests pass).
- **FAC-2**: `requirements.txt` has exactly one addition: `pyyaml==6.0.2`.
- **FAC-3**: `credentials.json` and `token.json` absent from committed files.
- **FAC-4**: No `datetime.utcnow()` in any new code.
- **FAC-5**: `app.py`, `scheduler.py`, `popup.py`, `calendar_writer.py`, `sync_job.py` not created or modified.
- **FAC-6**: `README.md` updated to add `drive_config.py`, `calendar_reader.py`, `compute.py` to Project Structure table.
- **FAC-7**: `build/tests.sh` runs without modification.
- **FAC-8**: `auth.py` not modified.

---

## Constraints

- Python 3.14 — no `datetime.utcnow()` (removed in 3.14); use `datetime.now(tz=...)`.
- Shell: fish. venv at git common root. Always `uv run` / `uv pip`.
- macOS only at runtime.
- No UI, no calendar writes, no scheduling in this feature.
- All-day events (missing `dateTime` key) silently skipped.
- `auth.py` must not be modified.
- All API calls mocked in unit tests — no live network calls in pytest.
- `CONFIG_FILE_ID` default `'1nPSl33iRhs5Jnv1SxNxdc9qHoID5J1UF'` — do not change this value.
- Config file format is YAML. `parse_config()` uses `yaml.safe_load()`. No regex-based markdown parsing.
- All configurable values come from the YAML file; sane defaults are fallback only — no value is permanently hardcoded.

---

## Non-Goals

- Writing to any calendar (NPC-0003).
- Popup or any UI (NPC-0002).
- Scheduling at a set time (NPC-0003).
- Live travel time via Maps API.
- Handling multi-day or all-day events.
- Writing the Drive config file.

---

## Definition of Done

- [ ] `drive_config.py` created: `CONFIG_FILE_ID`, `DEFAULT_CONFIG_YAML`, `read_config()`, `bootstrap_config()`, `write_config()`, `parse_config()` (YAML, all 12 keys).
- [ ] `calendar_reader.py` created: `LOCAL_TZ`, `get_tomorrow_range()`, `get_msi_time_blocks()`, `get_personal_events()`.
- [ ] `compute.py` created: `match_block_to_meeting()`, `compute_alarm()` (uses `config['baseline_event_title']` / `config['baseline_event_time']`).
- [ ] `config.yaml` created at project root with canonical default YAML.
- [ ] `requirements.txt` updated: `pyyaml==6.0.2` added.
- [ ] `tests/test_drive_config.py` — ≥ 12 cases, all passing.
- [ ] `tests/test_calendar_reader.py` — ≥ 6 cases, all passing.
- [ ] `tests/test_compute.py` — ≥ 8 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `README.md` updated with new files in Project Structure table.
- [ ] No `credentials.json` / `token.json` in staged files.
- [ ] No `datetime.utcnow()` in new code.
- [ ] `build/tests.sh` runs without modification.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 (`drive_config.py`) | None | US-2 (source files only) |
| US-2 (`calendar_reader.py`) | None | US-1 (source files only) |
| US-3 (`compute.py`) | US-1, US-2 shapes | Neither (depends on both) |

US-1 and US-2 source files can be written in parallel (different files, no shared state). US-3 source can be written once US-1 and US-2 dict shapes are defined in the spec (i.e., immediately — shapes are fixed above). Tests cannot run until venv is active.

---

## Proposed Schema Changes

None.

---

## Proposed Architecture Changes

None. New modules follow the flat project-root layout of `auth.py`, `app.py`, `main.py`.

---

## File Touch List

### Create
```
phantom-calendar/
├── drive_config.py               (US-1)
├── calendar_reader.py            (US-2)
├── compute.py                    (US-3)
├── config.yaml                   (US-1 — default config, committed)
└── tests/
    ├── test_drive_config.py      (US-1)
    ├── test_calendar_reader.py   (US-2)
    └── test_compute.py           (US-3)
```

State files:
```
docs/NPC-0001/
├── spec.md
├── decision.md
├── progress.md
├── US-1/decision.md
├── US-1/progress.md
├── US-2/decision.md
├── US-2/progress.md
├── US-3/decision.md
└── US-3/progress.md
```

### Modify
- `README.md` — add `drive_config.py`, `calendar_reader.py`, `compute.py`, `config.yaml` to Project Structure table.
- `requirements.txt` — add `pyyaml==6.0.2`.

### Do NOT touch
- `auth.py`, `app.py`, `main.py`
- `build/tests.sh`, `build/manual_tests.md`
- `tests/smoke_imports.py`, `tests/test_auth.py`, `tests/test_main.py`
