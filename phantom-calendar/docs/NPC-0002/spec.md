---
spec_hash: 'a56b1060543e'
---

# Spec: NPC-0002 — Confirmation Popup

## Clarifications from Codebase

### 1. compute_alarm() result dict — 7 keys (mapped from feature.md "structured result")

| feature.md term | code key | type |
|---|---|---|
| "first meeting name" | `result["first_meeting_name"]` | `str \| None` |
| "meeting start time" | `result["first_meeting_time"]` | `datetime \| None` (tz-aware) |
| "prep minutes" | `result["prep_minutes"]` | `int` |
| "computed alarm time" | `result["alarm_time"]` | `datetime \| None` (tz-aware) |
| "baseline match" | `result["is_baseline"]` | `bool` |
| (not displayed — non-goal) | `result["all_meetings"]` | `list` |
| "unknown MSI blocks" | `result["unknown_blocks"]` | `list` |

Source: `compute.py`, `compute_alarm()` return statements.

### 2. No-meetings vs. baseline-match detection

feature.md treats AC9 (no-meetings) and AC8 (baseline) as distinct display states. In `compute.py`, when no candidates are found, `compute_alarm()` returns `first_meeting_name=None` **and** `is_baseline=True`. When the first meeting matches the baseline, `first_meeting_name` is set and `is_baseline=True`.

Correct popup display-mode logic (check order matters):

1. `result["first_meeting_name"] is None` → **no-meetings mode** (AC9)
2. `result["is_baseline"] is True` → **baseline mode** (AC8)
3. Otherwise → **normal mode**

### 3. project.md Step 7 ConfirmationPopup — reference class

The project.md template uses `tk.Toplevel` with a parent window. NPC-0002's popup has no parent (triggered by a headless nightly sync). The actual class must use `tk.Tk()` directly as the root window, not `tk.Toplevel`.

### 4. popup.py location and isolation

`popup.py` lives at project root. It must not import `auth`, `calendar_reader`, `drive_config`, or `compute`. The `compute_alarm()` result dict is passed in at construction time.

### 5. _parse_alarm_override — signature

`_parse_alarm_override(self, text: str, reference_dt: datetime) -> datetime | None`

Takes the Entry widget text and the reference datetime (`result["first_meeting_time"]`) explicitly. Output is a tz-aware datetime using `reference_dt.date()` and `reference_dt.tzinfo`. Explicit args make it directly unit-testable.

### 6. Response dict by display mode

| Mode | Action | `confirmed` | `alarm_time` | `skipped` |
|---|---|---|---|---|
| Normal | Write to Calendar | `True` | parsed datetime | `False` |
| Normal | Skip | `False` | `None` | `True` |
| Normal | Dismiss (WM_DELETE_WINDOW) | same as Write to Calendar | | |
| Baseline | Skip or Dismiss | `False` | `None` | `False` |
| No-meetings | Skip or Dismiss | `False` | `None` | `True` |

---

## Human-Required Steps

### H-1 — Visual focus test (AC11)
Trigger the popup with a real compute result and verify the window appears above all other open windows and claims keyboard focus. Cannot be automated without a running display. Follow `MT-2.11` in `build/manual_tests.md`.

No pip install required — `tkinter` is stdlib in Python 3.14.

---

## User Stories

---

### US-1: Implement ConfirmationPopup

**Story:** As the nightly sync, I need a tkinter confirmation popup that receives the `compute_alarm()` result dict, displays tomorrow's first meeting and computed alarm time, allows the user to adjust the alarm time, and returns a structured `{"confirmed", "alarm_time", "skipped"}` response so that NPC-0003 can decide whether to write to Google Calendar.

#### Acceptance Criteria

- AC1.1 **[feature AC1]**: `ConfirmationPopup(result).show()` opens a `tk.Tk()` window regardless of display mode (normal, baseline, no-meetings).

- AC1.2 **[feature AC2]**: When `result["first_meeting_name"] is not None`, the window displays: meeting name, `result["first_meeting_time"]` formatted as `HH:MM`, and `result["prep_minutes"]` as prep minutes.

- AC1.3 **[feature AC3]**: In normal mode, a `tk.Entry` pre-populated with `result["alarm_time"]` formatted as `HH:MM` is shown and editable by the user.

- AC1.4 **[feature AC4]**: In normal mode, when the Entry contains a malformed value (not `HH:MM`, `HH > 23`, or `MM > 59`), clicking "Write to Calendar" is blocked and an inline `tk.Label` error is shown indicating the expected format `HH:MM`.

- AC1.5 **[feature AC5]**: In normal mode with a valid alarm Entry, clicking "Write to Calendar" destroys the window and `show()` returns `{"confirmed": True, "alarm_time": <parsed tz-aware datetime>, "skipped": False}`.

- AC1.6 **[feature AC6]**: Clicking "Skip" in any mode destroys the window and `show()` returns `{"confirmed": False, "alarm_time": None, "skipped": True}`.

- AC1.7 **[feature AC7]**: In normal mode, closing via OS close button (`WM_DELETE_WINDOW`) triggers the same path as "Write to Calendar". Implemented by binding `WM_DELETE_WINDOW` to `_on_confirm`.

- AC1.8 **[feature AC8]**: When `result["is_baseline"] is True` and `result["first_meeting_name"] is not None`: show meeting info, show non-editable alarm time label, show "No new calendar event needed", omit "Write to Calendar" button. Skip or Dismiss returns `{"confirmed": False, "alarm_time": None, "skipped": False}`.

- AC1.9 **[feature AC9]**: When `result["first_meeting_name"] is None`: show "No meetings found for tomorrow", omit meeting info, alarm field, and "Write to Calendar" button. Skip or Dismiss returns `{"confirmed": False, "alarm_time": None, "skipped": True}`.

- AC1.10 **[feature AC10]**: When `len(result["unknown_blocks"]) > 0`, a non-blocking warning section lists each unknown block with its start time formatted as `HH:MM`, e.g.: `"Unknown block at 14:00 — 30 min prep applied"` (one line per block). Shown in all display modes above the alarm field.

- AC1.11 **[feature AC11] [MANUAL TEST MT-2.11]**: On `show()`, the window calls `self._root.lift()`, `self._root.attributes("-topmost", True)`, and `self._root.focus_force()` before entering the event loop.

#### Test Coverage (`tests/test_popup.py`)

Mocking strategy: patch `popup.tk` via `unittest.mock.patch("popup.tk")` in `setUp`. Call button callbacks (`_on_confirm`, `_on_skip`) directly; assert `_response` dict.

**TestParseAlarmOverride:**
- `test_valid_hhmm_returns_correct_datetime` — `"09:25"` with tz-aware reference dt → datetime with hour=9, minute=25, same tzinfo
- `test_parsed_datetime_preserves_timezone` — tzinfo of output matches `reference_dt.tzinfo`
- `test_invalid_format_returns_none` — `"9am"`, `"930"`, `""`, `"9:5:0"` each return `None`
- `test_out_of_range_hour_returns_none` — `"25:00"` → `None`
- `test_out_of_range_minute_returns_none` — `"12:60"` → `None`

**TestConfirmationPopupCallbacks:**
- `test_on_confirm_response_confirmed_true` — after `_on_confirm()`, `_response["confirmed"]` is `True` and `_response["skipped"]` is `False`
- `test_on_confirm_response_alarm_time_is_datetime` — `_response["alarm_time"]` is a `datetime` instance
- `test_on_skip_response_skipped_true` — after `_on_skip()`, response is `{"confirmed": False, "alarm_time": None, "skipped": True}`
- `test_on_dismiss_same_as_confirm` — dismiss handler with valid Entry produces same result as `_on_confirm()`
- `test_confirm_blocked_when_entry_invalid` — `_on_confirm()` with malformed Entry: `_root.destroy` not called; error label text is non-empty
- `test_response_dict_has_exactly_three_keys` — response dict has exactly keys `{"confirmed", "alarm_time", "skipped"}`

**TestConfirmationPopupDisplayModes:**
- `test_no_meetings_mode_omits_write_button` — `first_meeting_name=None` → `_write_btn` is `None`
- `test_baseline_mode_omits_write_button` — `is_baseline=True` with meeting → `_write_btn` is `None`
- `test_normal_mode_has_write_button` — normal result → `_write_btn` is not `None`
- `test_unknown_blocks_warning_present` — `unknown_blocks` non-empty → `_warning_label` is not `None` and contains the block's start time formatted as `HH:MM`
- `test_unknown_blocks_warning_absent_when_empty` — `unknown_blocks == []` → `_warning_label` is `None`
- `test_unknown_blocks_warning_shows_multiple_blocks` — two unknown blocks → warning text contains both start times

#### Dependencies

- `compute.py` (NPC-0001) — present in worktree (result dict shape only; not imported).
- `tkinter` — stdlib, Python 3.14; no install required.

---

## Feature-Wide Acceptance Criteria

- `show()` always returns exactly 3 keys: `confirmed` (bool), `alarm_time` (`datetime | None`), `skipped` (bool).
- `popup.py` never calls `sys.exit()`.
- `popup.py` has no imports from `auth`, `calendar_reader`, `drive_config`, or `compute`.
- All `datetime` values passed into and returned from `popup.py` are timezone-aware; `tzinfo` is preserved in the response.
- `popup.py` does not write to any file, calendar, or external service.

---

## Constraints

- Python 3.14. No `datetime.utcnow()` (rune `python-version-compatibility`).
- Shell: fish; environment via `uv` (rune `venv-and-uv-conventions`).
- tkinter is stdlib — no `requirements.txt` change.
- macOS only.
- `popup.py` at project root.
- `compute_alarm()` result dict is the only input; no direct API calls in `popup.py`.
- No calendar writing or scheduling in this feature.

---

## Non-Goals

- Writing to Google Calendar (NPC-0003).
- Triggering or scheduling the popup (NPC-0003).
- Configurable show/hide behavior for baseline or no-meetings cases.
- Snooze / "remind me later" behavior.
- Displaying all meetings for tomorrow (only first meeting shown).

---

## Definition of Done

- [ ] `popup.py` at project root with `ConfirmationPopup` class and `show()` method.
- [ ] All ACs 1.1–1.10 verified by automated tests.
- [ ] AC1.11 verified by manual test `MT-2.11`.
- [ ] `tests/test_popup.py` — all named tests pass via `uv run python -m pytest tests/ -v`.
- [ ] `tests/smoke_imports.py` — `popup` added to import list and passes.
- [ ] `build/manual_tests.md` — entry `MT-2.11` added.
- [ ] `README.md` — `popup.py` in Project Structure table; `MT-2.11` row in Manual tests table.
- [ ] No credentials or token files staged or committed.
- [ ] `build/tests.sh` passes without modification.

---

## Parallelization Analysis

Single story — no inter-story parallelism needed. Within US-1, core implementation and tests can proceed together once the public API is agreed (fixed in this spec).

---

## Proposed Schema Changes

None.

---

## Proposed Architecture Changes

None. `popup.py` is a standalone module at project root, called synchronously by the nightly sync (NPC-0003); returns a plain dict.

---

## File Touch List

| File | Action |
|---|---|
| `popup.py` | Create |
| `tests/test_popup.py` | Create |
| `tests/smoke_imports.py` | Modify — add `popup` import |
| `build/manual_tests.md` | Modify — add MT-2.11 |
| `README.md` | Modify — new source file, new MT row |
| `build/tests.sh` | No change |
| `requirements.txt` | No change |
