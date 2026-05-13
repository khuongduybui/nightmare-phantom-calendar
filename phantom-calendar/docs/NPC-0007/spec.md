---
spec_hash: ''
---

# NPC-0007 Spec — Unknown Meeting Classification

## Clarifications from Codebase

### Term → Code Mappings

| feature.md term | Code identifier | Location |
|---|---|---|
| "unknown MSI blocks" | `result["unknown_blocks"]` — `list[dict]` with `start`, `end` keys | `compute.py::compute_alarm()` |
| "meeting types dropdown" | `choose from list` AppleScript command | `sync_job._show_popup()` |
| "prep time for type" | `config["meeting_type_prep"][type_name]` — int or `"travel+N"` string | `drive_config.parse_config()` |
| "classification returned" | `popup_response["classifications"]` — `list[dict]` | `sync_job._show_popup()` |
| "write back to Drive config" | `drive_config.append_recurring_meeting()` + `write_config()` | `drive_config.py` |
| "new recurring meeting entry" | dict matching `config["recurring_meetings"]` item shape | `config.yaml` |
| "osascript dialog" | `sync_job._osascript()` — subprocess wrapper | `sync_job.py` |

### osascript `choose from list` Mechanics

AppleScript's `choose from list` command shows a native macOS list picker:
```applescript
set selected to choose from list {"Type A", "Type B", "Skip"} ¬
    with prompt "What type of meeting is this?" ¬
    default items {"Skip"} ¬
    with title "Phantom Calendar"
```
Returns `false` if cancelled, or `{"selected item"}` (a list with one element).

This is spawned as a subprocess in `_osascript()`. The command must be in a single `osascript -e` call.

### `meeting_type_prep` values

Values are either `int` (pure minutes) or `str` like `"travel+10"`. Only integer values can be directly used as `prep_minutes`. Travel-time entries are skipped from the classification list (cannot be resolved without location data).

### Response shape extension

`_show_popup()` currently returns:
```python
{"confirmed": bool, "alarm_time": datetime | None, "skipped": bool}
```

Extended with:
```python
{"confirmed": bool, "alarm_time": datetime | None, "skipped": bool,
 "classifications": list[dict]}
```

Each classification dict:
```python
{"start_time": str,  # ISO format of block["start"]
 "meeting_type": str,  # selected type name
 "prep_minutes": int}  # from meeting_type_prep
```

### Mismatch: feature.md AC2 (live recalculation)

osascript dialogs are modal and sequential — they cannot do "live" recalculation as the user changes a dropdown. The implementation uses a two-step approach:
1. Show the main alarm confirmation dialog (existing behavior)
2. For each unknown block, show a separate `choose from list` dialog sequentially
3. Recalculate and show updated alarm in the final summary

This satisfies the intent of AC2 without requiring a reactive UI.

---

## Human-Required Steps

None. All ACs are fully automatable via mocked tests.

---

## User Stories

---

### US-1 — Classification UI in _show_popup()

**Story:** As the nightly sync, I want `_show_popup()` to show a meeting type picker for each unknown MSI block and return the classifications in the response, so the user can identify unknown meetings.

**Acceptance Criteria:**

- AC1.1: When `result["unknown_blocks"]` is non-empty, `_show_popup()` shows a `choose from list` dialog for each block (in order of start time) before the main alarm confirmation dialog. (feature.md AC1)
- AC1.2: The type list offered is derived from `config["meeting_type_prep"]` — only entries with integer prep values are included (travel-time entries like `"travel+10"` are excluded). A `"Skip (keep default)"` option is always appended. (feature.md AC1, AC6)
- AC1.3: If the user selects a type (not Skip), the alarm time is recalculated as `block["start"] - timedelta(minutes=prep_minutes)` and replaces `result["alarm_time"]` for display in the main dialog. If multiple unknown blocks are present and the earliest becomes the first meeting, that block's alarm is used. (feature.md AC2)
- AC1.4: The main alarm confirmation dialog (existing `_show_popup` behavior) runs after all classification dialogs and displays the (possibly updated) alarm time. (feature.md AC2)
- AC1.5: `_show_popup()` returns `classifications` in the response dict — a list of dicts with `start_time` (ISO str), `meeting_type` (str), `prep_minutes` (int). Only non-skipped selections are included. (feature.md AC3)
- AC1.6: If the result is baseline or has no meetings, no classification dialogs are shown. (feature.md AC5)
- AC1.7: `config` dict must be passed into `_show_popup()` as a parameter: `_show_popup(result, config)`. `sync_job.run_nightly_sync()` passes config accordingly.
- AC1.8: No `datetime.utcnow()`.

**Test coverage (`tests/test_classification_ui.py`):**
- `test_no_classification_dialog_when_no_unknown_blocks` — mock `_osascript`; result with no unknown blocks; assert `choose from list` not called.
- `test_classification_dialog_shown_for_each_unknown_block` — two unknown blocks; assert `_osascript` called twice with `choose from list` before the main dialog.
- `test_selected_type_updates_alarm_time` — user selects "Daily standup" (5 min prep); block starts at 09:30; assert alarm recalculated to 09:25.
- `test_skipped_classification_not_in_response` — user selects Skip; assert `classifications` list is empty.
- `test_non_skipped_classification_in_response` — user selects a type; assert `classifications` contains correct `start_time`, `meeting_type`, `prep_minutes`.
- `test_travel_time_types_excluded_from_list` — config has `"In-person (local)": "travel+10"`; assert that option not offered.
- `test_baseline_result_skips_classification` — `is_baseline=True`; assert no `choose from list` call.

**Dependencies:** NPC-0001 (config dict shape), NPC-0002 (popup pattern), NPC-0006 (osascript popup).

---

### US-2 — Write Classifications Back to Drive Config

**Story:** As the nightly sync, I want confirmed classifications to be appended to `recurring_meetings` in the Drive config file, so future runs recognize those meetings automatically.

**Acceptance Criteria:**

- AC2.1: `drive_config.append_recurring_meetings(classifications: list[dict], config: dict) -> str` builds an updated config dict with each classification appended to `config["recurring_meetings"]` as a new entry, serializes to YAML, calls `write_config()`, and returns the updated YAML string. (feature.md AC4)
- AC2.2: Each appended recurring meeting entry has: `name` (from `meeting_type` + start time, e.g. `"Daily standup (09:30)"`), `start` (HH:MM from block start time), `end` (HH:MM estimated as start + prep_minutes), `days` (default `[Mon, Tue, Wed, Thu, Fri]`), `prep_minutes` (int), `notes` (`"Auto-classified by Phantom Calendar"`).
- AC2.3: `run_nightly_sync()` in `sync_job.py` calls `append_recurring_meetings()` after `run_calendar_write()` if `popup_response["classifications"]` is non-empty and `popup_response["confirmed"]` is True.
- AC2.4: If `append_recurring_meetings()` raises any exception, the error is logged to stderr and the sync is considered complete — the Drive config write failure is non-fatal. (feature.md AC7)
- AC2.5: If `popup_response["skipped"]` is True or `confirmed` is False, no Drive config write occurs.

**Test coverage (`tests/test_classification_write.py`):**
- `test_append_recurring_meetings_adds_entry` — mock `write_config`; assert the new meeting appears in the written YAML.
- `test_append_recurring_meetings_preserves_existing` — existing meeting in config; assert it is still present after append.
- `test_no_write_when_classifications_empty` — assert `write_config` not called.
- `test_no_write_when_skipped` — `skipped=True`; assert `write_config` not called.
- `test_write_failure_is_non_fatal` — `write_config` raises; assert no exception propagates from `run_nightly_sync`.

**Dependencies:** US-1 (`classifications` in response).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: No `datetime.utcnow()`.
- **FAC-3**: `auth.py` not modified.
- **FAC-4**: `credentials.json` and `token.json` absent from committed files.
- **FAC-5**: `build/tests.sh` passes without modification.

---

## Constraints

- Python 3.14. No `datetime.utcnow()`.
- Fish shell, uv conventions.
- Only `sync_job.py` and `drive_config.py` are modified.
- `compute.py`, `calendar_writer.py`, `popup.py`, `app.py`, `scheduler.py` are NOT modified.
- Travel-time prep values (`"travel+N"`) are excluded from the classification list.
- Classification is per-sync-run only — not persisted in any local state file.

---

## Non-Goals

- Retroactively classifying past unknown blocks.
- Editing or deleting existing recurring meeting entries.
- UI for managing the full recurring meetings list.
- Classification of personal calendar events.

---

## Definition of Done

- [ ] `sync_job.py` updated: `_show_popup(result, config)` with classification dialogs; `run_nightly_sync` passes config to `_show_popup` and calls `append_recurring_meetings` after write.
- [ ] `drive_config.py` updated: `append_recurring_meetings(classifications, config)`.
- [ ] `tests/test_classification_ui.py` — ≥ 7 cases, all passing.
- [ ] `tests/test_classification_write.py` — ≥ 5 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] `build/tests.sh` passes without modification.
- [ ] No credentials in staged files.

---

## Parallelization Analysis

| Story | Depends on | Can parallelize with |
|---|---|---|
| US-1 (`_show_popup` extension) | None | — |
| US-2 (Drive config write) | US-1 (`classifications` key in response) | Cannot parallelize |

---

## File Touch List

### Modify
- `sync_job.py` — extend `_show_popup`, update `run_nightly_sync`
- `drive_config.py` — add `append_recurring_meetings()`

### Create
- `tests/test_classification_ui.py`
- `tests/test_classification_write.py`

### Do NOT touch
- `auth.py`, `app.py`, `main.py`, `scheduler.py`, `requirements.txt`
- `compute.py`, `calendar_writer.py`, `popup.py`, `calendar_reader.py`
