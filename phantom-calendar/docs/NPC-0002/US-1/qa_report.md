---
phase: QA
date: 2026-05-12
status: PASS
---

# QA Report — US-1 (ConfirmationPopup)

## AC Verification

| AC | Status | Evidence |
|----|--------|---------|
| AC1.1 — show() opens tk.Tk() in all modes | ✅ PASS | All 3 display modes tested; `_build_ui` called in each |
| AC1.2 — meeting info displayed | ✅ PASS | `_build_normal` and `_build_baseline` render name/time/prep |
| AC1.3 — editable alarm Entry in normal mode | ✅ PASS | `_alarm_entry` set in normal mode; `None` in others |
| AC1.4 — invalid time blocked with inline error | ✅ PASS | `test_confirm_blocked_when_entry_invalid` — destroy not called, error label set |
| AC1.5 — Write to Calendar returns confirmed=True | ✅ PASS | `test_on_confirm_response_confirmed_true`, `test_on_confirm_response_alarm_time_is_datetime` |
| AC1.6 — Skip returns confirmed=False, skipped=True | ✅ PASS | `test_on_skip_response_skipped_true` |
| AC1.7 — WM_DELETE_WINDOW = confirm in normal mode | ✅ PASS | `test_on_dismiss_same_as_confirm`; protocol bound to `_on_confirm` |
| AC1.8 — Baseline: no Write button, correct response | ✅ PASS | `test_baseline_mode_omits_write_button`, `test_baseline_skip_returns_skipped_false` |
| AC1.9 — No-meetings: no Write button, skipped=True | ✅ PASS | `test_no_meetings_mode_omits_write_button`, `test_no_meetings_skip_returns_skipped_true` |
| AC1.10 — Unknown blocks warning with start times | ✅ PASS | `test_unknown_blocks_warning_present`, `test_unknown_blocks_warning_shows_multiple_blocks` |
| AC1.11 — lift/topmost/focus_force called | ✅ PASS | Code verified in `show()`; MT-2.11 for visual confirmation |

## Feature-Wide AC Check
- `show()` returns exactly 3 keys ✓ (`test_response_dict_has_exactly_three_keys`)
- No `sys.exit()` in popup.py ✓
- No imports of auth/calendar_reader/drive_config/compute ✓
- All datetimes are tz-aware ✓ (`test_parsed_datetime_preserves_timezone`)
- No file/calendar writes ✓

## Test Run
```
19 passed, 5 subtests — test_popup.py (Python 3.14.4)
56 passed, 5 subtests — full suite
```

## Findings
None. All ACs satisfied.

## Manual Test Required
MT-2.11 — visual focus test — deferred to developer.
