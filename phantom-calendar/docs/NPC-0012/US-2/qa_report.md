## QA Report — US-2: Surface Unknown Locations in Popup and Write to Drive Config — 2026-05-16T00:00:00

### Missing Tests
- No dedicated test verifying dialog prompt *content* (AC 2.2 verifies call count, not the actual title/location text passed to osascript). Acceptable since content correctness is enforced by code inspection.
- No test for negative travel-minutes input (e.g., `"-5"`). The `travel_minutes <= 0` guard covers this path, but no explicit test exercises it. Low risk — guarded correctly.

### Negative Tests (minimum 3)
- `test_zero_input_excluded`: zero input yields empty location_travel_minutes (AC 2.10)
- `test_blank_input_excluded`: blank input yields empty result (AC 2.10)
- `test_non_integer_input_excluded`: non-integer string yields empty result (AC 2.4)
- `test_osascript_failure_treated_as_zero`: rc != 0 treated as skip, no crash (AC 2.11)
- `test_append_locations_failure_non_fatal`: Drive write error does not propagate (AC 2.8)
- `test_prompt_not_called_for_empty_unknown_locs`: empty unknown_personal_locations skips prompt (AC 2.9)

### Edge Cases (minimum 3)
- `test_two_events_same_location_one_dialog`: grouping by location — two events → one dialog
- `test_two_different_locations_two_dialogs`: two distinct locations → two dialogs
- `test_alarm_unchanged_when_event_is_later`: alarm not moved later when event start minus travel > current alarm
- `test_empty_list_returns_empty_dict_and_unchanged_alarm`: empty input returns ({}. unchanged alarm)
- `test_existing_location_not_overwritten`: existing config entry not clobbered by append_locations

### Security Checklist
- [ ] SQL/command injection? — osascript dialogs embed calendar `location` and `title` strings without escaping. See **Security Review** for details.
- [x] Auth bypass? — No auth changes.
- [x] Sensitive data in logs/responses? — Drive error logged to stderr without leaking config data.
- [x] Input validation at boundaries? — user input from osascript validated (int(), <= 0 guard, rc check).
- [x] Confused deputy / privilege escalation? — No role or permission changes.

### Performance Considerations
- `_prompt_unknown_locations` runs one `subprocess.run(["osascript", ...])` per unique location. Each call blocks on user input (up to 5 min timeout). This is expected and matches the existing `_classify_unknown_blocks` pattern.
- The grouping pass (`groups.setdefault`) is O(n) in unknown location entries — acceptable for realistic event counts.

### Untested Assumptions
- Personal events with unknown locations always have 0 existing fixed prep (from the Home location fallback). The alarm recalculation `event_start - travel_minutes` omits any meeting_type-based prep already computed for the event. This is correct today since unknown-location personal events fall back to Home=0 travel, but could become wrong if a personal event has meeting_type prep AND an unknown location simultaneously.
- `config["msi_calendar_id"]` always present. `append_locations` accesses it directly (not via `.get()`). If absent, a `KeyError` is thrown — caught non-fatally by the try/except in `run_nightly_sync`. Consistent with the existing `append_recurring_meetings` pattern.

### How This Fails in Prod
- User has a personal event at an exotic location containing a double-quote (`"`). The osascript string boundary breaks; the dialog either fails to display or shows garbled text. The rc != 0 guard catches failures gracefully, so no crash — but the location is silently skipped.
- Drive config write fails (network/auth issue during `append_locations`). Error logged to stderr but location mappings lost — user re-prompted next sync.
- User enters a very large travel-minutes number (e.g., 999). This passes validation and gets written to Drive config; on next sync the alarm may fire extremely early. No upper-bound validation exists.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|---|---|---|---|
| Non-zero integer | `"45"`, rc=0 | `{location: 45}` in result | ✓ `test_non_zero_integer_included_in_result` |
| Zero input | `"0"`, rc=0 | empty dict | ✓ `test_zero_input_excluded` |
| Blank input | `""`, rc=0 | empty dict | ✓ `test_blank_input_excluded` |
| Non-integer string | `"abc"`, rc=0 | empty dict | ✓ `test_non_integer_input_excluded` |
| Cancelled (rc≠0) | `"30"`, rc=1 | empty dict, alarm unchanged | ✓ `test_osascript_failure_treated_as_zero` |
| Two events, same location | two entries | one dialog call | ✓ `test_two_events_same_location_one_dialog` |
| Two different locations | two entries | two dialog calls | ✓ `test_two_different_locations_two_dialogs` |
| Alarm moved earlier | event 08:00, current alarm 09:00, travel=30 | alarm=07:30 | ✓ `test_alarm_recalculated_when_event_is_earlier` |
| Alarm not moved later | event 14:00, current alarm 07:00, travel=5 | alarm=07:00 | ✓ `test_alarm_unchanged_when_event_is_later` |
| Empty unknown_locs | `[]` | `({}, unchanged alarm)` | ✓ `test_empty_list_returns_empty_dict_and_unchanged_alarm` |
| No-meetings popup path | `first_meeting_name=None` | `location_travel_minutes: {}` key present | ✓ `test_no_meetings_returns_location_travel_minutes_key` |
| Baseline popup path | `is_baseline=True` | `location_travel_minutes` key present | ✓ `test_baseline_returns_location_travel_minutes_key` |
| Skipped popup path | user skips dialog | `location_travel_minutes` key present | ✓ `test_skipped_returns_location_travel_minutes_key` |
| Unknown locs prompt called | non-empty `unknown_personal_locations` | `_prompt_unknown_locations` called, result merged | ✓ `test_unknown_locs_prompt_called_and_merged` |
| Empty unknown_locs, no prompt | `unknown_personal_locations=[]` | `_prompt_unknown_locations` not called | ✓ `test_prompt_not_called_for_empty_unknown_locs` |
| New location written to Drive | `{"Clinic": 45}` | YAML written with Clinic=45 | ✓ `test_new_locations_written_to_drive` |
| Existing location not overwritten | existing Clinic=20, new Clinic=45 | Clinic remains 20 | ✓ `test_existing_location_not_overwritten` |
| append_locations called | non-empty location_travel_minutes | `append_locations` invoked with correct args | ✓ `test_append_locations_called_when_non_empty` |
| append_locations not called | empty location_travel_minutes | `append_locations` not invoked | ✓ `test_append_locations_not_called_when_empty` |
| Drive failure non-fatal | `append_locations` raises | no exception propagated, calendar write still ran | ✓ `test_append_locations_failure_non_fatal` |
| Negative travel minutes | `"-5"` | excluded (<=0 guard) | ✗ not explicitly tested |

### Validation Runs
- Lint: FAIL — `uv tool run ruff check sync_job.py drive_config.py tests/test_sync_job.py` finds 5 issues (1 new in diff, 4 pre-existing). See Code Review / Issues. Note: ruff is not installed in the project venv (not in requirements.txt); Implementer ran ruff as a personal tool and reported PASS. QA ran via `uv tool run ruff` (latest ephemeral install).
  - New in diff: `tests/test_sync_job.py:236` F401 — `timedelta` imported but unused
  - Pre-existing (not introduced by this diff): `sync_job.py:365` F541, `tests/test_sync_job.py:3,4,6` F401
- Unit tests: PASS — `bash build/tests.sh` — 166/166 passed

### Code Review

`tests/test_sync_job.py:236`: L236: `from datetime import datetime, timedelta` — `timedelta` unused in `test_alarm_unchanged_when_event_is_later`. Remove extraneous `timedelta` import (copy-paste from adjacent test). 🟡 risk: unused import is lint noise; minor.

`sync_job.py:181`: L181: `from datetime import datetime as _dt` inside a for-loop body — deferred import inside loop is unusual. Import is cached after first execution so no perf issue, but `timedelta` is already imported at function top (L136); move `datetime` import to function top alongside it. 🔵 nit.

`sync_job.py:149-152`: L152: `f"How many minutes of travel time?"` — f-string with no interpolation placeholder (matches existing F541 pattern in codebase). Remove the `f` prefix. 🔵 nit.

`tests/test_sync_job.py:9-18`: MOCK_CONFIG (pre-existing global) is missing `msi_calendar_id`. `run_nightly_sync` tests that use it pass because `append_locations` is mocked, so the key is never accessed. But the mock no longer reflects the full config shape. 🔵 nit.

`tests/test_sync_job.py:33-37`: MOCK_POPUP_RESPONSE (pre-existing global) is missing `location_travel_minutes`. The new `run_nightly_sync` code handles this correctly via `.get()`. But the mock drifts from the real return shape. 🔵 nit (pre-existing hygiene issue, not introduced by this diff).

### UI Review
No UI-scope changes.

### AWS Review
No AWS changes in this diff.

### Security Review

`sync_job.py:147-162`: Location string from calendar event data interpolated directly into an AppleScript double-quoted string (e.g., `f'"{prompt_text}"'`). A location containing `"` breaks the string boundary. Worst case: dialog fails to display, rc != 0, location is silently skipped (graceful). Risk is low for a local app with trusted calendar data as the source. The existing `_classify_unknown_blocks` establishes the same pattern. Recommend escaping `"` → `\\"` in location/title strings before interpolation as a robustness improvement. INFO severity for local app with no external attack surface.

### Backlog Candidates
- Finding Key: `LOW|phantom-calendar/sync_job.py|365|f-string-without-placeholder-pre-existing`
  - Finding: LOW: `sync_job.py:L365`: `print(f"[DEBUG] --- Alarm result ---")` — f-string with no placeholders (F541, pre-existing before US-2 diff)
  - Why deferred: pre-existing before this story; not introduced by US-2 diff
  - Suggested next action: cleanup story or opportunistic fix
  - Backlog action: appended to new NPC-0012/backlog.md

- Finding Key: `LOW|phantom-calendar/tests/test_sync_job.py|3|unused-imports-sys-threading-call-pre-existing`
  - Finding: LOW: `tests/test_sync_job.py:L3,4,6`: `sys`, `threading`, `call` imported but unused (F401, pre-existing before US-2 diff)
  - Why deferred: pre-existing before this story; not introduced by US-2 diff
  - Suggested next action: cleanup story or opportunistic fix
  - Backlog action: appended to new NPC-0012/backlog.md

- Finding Key: `INFO|phantom-calendar/sync_job.py|147|osascript-string-injection-calendar-data`
  - Finding: INFO: `sync_job.py:L147-162`: calendar location/title strings interpolated into osascript without escaping `"` characters
  - Why deferred: local app pattern; consistent with existing `_classify_unknown_blocks`; graceful failure on dialog error
  - Suggested next action: add `str.replace('"', '\\"')` escaping in a future hardening story
  - Backlog action: appended to new NPC-0012/backlog.md

### Justification Review
No Implementer justifications in decision.md for LOW/INFO findings (decision.md only has the initial state entry). The following LOW findings are unresolved:

- Finding: LOW: `tests/test_sync_job.py:L236`: `timedelta` imported but unused in `test_alarm_unchanged_when_event_is_later`
  - Implementer justification summary: none provided
  - QA decision: rejected (no justification present)
  - QA analysis: This is a one-line fix (remove `timedelta` from the import). No design trade-off involved. There is no reasonable justification for leaving an unused import. Implementer must remove `timedelta` from `from datetime import datetime, timedelta` on line 236, making it `from datetime import datetime`.
  - Reviewer context: ruff F401; flagged only in new diff code (not pre-existing); must be fixed before PASS

### Human Review Queue
(empty — no HUMAN_REVIEW_PENDING findings)

### QA Loop Decision
- REWORK_REQUIRED
- 1 unresolved LOW finding without decision.md justification: unused `timedelta` import at `tests/test_sync_job.py:236`. All HIGH/MEDIUM findings: none. All ACs covered. Fix the import and re-run QA.

### Issues

#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
- L1: `tests/test_sync_job.py:L236` — `timedelta` imported but unused in `test_alarm_unchanged_when_event_is_later`; remove from `from datetime import datetime, timedelta`. **No decision.md justification. Must fix or justify.**

#### INFO
- I1: `sync_job.py:L181` — deferred `from datetime import datetime as _dt` inside for-loop body; move to function top alongside the existing `from datetime import timedelta` import at L136.
- I2: `sync_job.py:L152` — `f"How many minutes of travel time?"` is an f-string without placeholders; remove `f` prefix.
- I3: Alarm recalculation in `_prompt_unknown_locations` uses only `travel_minutes` (omits any existing fixed prep for the personal event). Correct for current use case (unknown location personal events have 0 existing travel prep) but not generalized per spec note. No test exercises the combined-prep case.
- I4: `tests/test_sync_job.py` MOCK_POPUP_RESPONSE missing `location_travel_minutes` key — pre-existing mock drift; not breaking since `.get()` is used.

### Spec Review

#### AC Coverage
| AC | Status | Notes |
|---|---|---|
| 2.1 | ✓ | `_show_popup` calls `_prompt_unknown_locations` when `unknown_personal_locations` non-empty and not baseline |
| 2.2 | ✓ | Groups by location string; one dialog per unique location |
| 2.3 | ✓ (simplified) | `candidate_alarm = event_start - travel_minutes`; omits existing_fixed (0 for unknown-location personal events — equivalent result) |
| 2.4 | ✓ | Only non-zero integers included |
| 2.5 | ✓ | `location_travel_minutes` in all return paths of `_show_popup` |
| 2.6 | ✓ | Placed after `append_recurring_meetings` block in `run_nightly_sync` |
| 2.7 | ✓ | Merges with `{**new, **existing}`; existing not overwritten |
| 2.8 | ✓ | try/except wraps `append_locations`; failure logs to stderr |
| 2.9 | ✓ | Empty list returns `({}, alarm)`; `_prompt_unknown_locations` not called |
| 2.10 | ✓ | `travel_minutes <= 0` guard + blank check |
| 2.11 | ✓ | rc != 0 → `continue` (no crash, no write) |
| 2.12 | ✓ | All 4 `_show_popup` return paths include `location_travel_minutes` |
| 2.13 | ✓ | 20 new tests covering 2.4–2.11 in 4 test classes |

#### Out-of-scope Changes
None detected. All changed lines are traceable to US-2 ACs.

### Rune Review
- `update-build-tests-sh`: no new test files, no structural change to `tests/` — no action needed ✓
- `update-manual-tests-md`: no manual ACs in US-2 — no action needed ✓
- `update-readme`: no new source files or dependencies — no action needed ✓
- `no-credentials-in-git`: no credentials in diff ✓
- `python-version-compatibility`: no deprecated APIs; `datetime.fromisoformat()` is available ✓
- `no-tkinter-in-rumps-process`: uses osascript throughout ✓
- `venv-and-uv-conventions`: ruff not in project venv — Implementer used personal ruff install for lint claim; no project-standard lint tool configured (no ruff in requirements.txt, no build/ruff.toml). Backlog candidate: add ruff to requirements/build pipeline.
- `local-state-files-in-gitignore`: no new state files ✓

---

## QA Report — US-2: Surface Unknown Locations in Popup and Write to Drive Config — 2026-05-16T01:00:00

### Missing Tests
None. Prior-report coverage unchanged. The single-line import fix introduces no logic paths.

### Negative Tests (minimum 3)
Unchanged from prior report — all 6 negative tests confirmed present and passing.

### Edge Cases (minimum 3)
Unchanged from prior report — all 5 edge cases confirmed present and passing.

### Security Checklist
- [ ] SQL/command injection? — osascript string injection INFO finding unchanged from prior report; deferred to backlog (INFO: `sync_job.py:L147-162`).
- [x] Auth bypass? — No auth changes.
- [x] Sensitive data in logs/responses? — Unchanged.
- [x] Input validation at boundaries? — Unchanged.
- [x] Confused deputy / privilege escalation? — Unchanged.

### Performance Considerations
Unchanged from prior report.

### Untested Assumptions
Unchanged from prior report.

### How This Fails in Prod
Unchanged from prior report.

### Test Matrix
Unchanged from prior report. The `timedelta` import removal does not affect any test logic.

### Validation Runs
- Lint: PASS (diff-scope) — `uv tool run ruff check sync_job.py drive_config.py tests/test_sync_job.py` — 4 pre-existing findings remain (already backlog-deferred in prior QA report, not introduced by US-2 diff); 0 new findings in current diff. The `timedelta` F401 (was at `tests/test_sync_job.py:L236`) is confirmed gone — import on that line now reads `from datetime import datetime`.
- Unit tests: PASS — `bash build/tests.sh` — 166/166 passed.

### Code Review
`tests/test_sync_job.py:238`: fix confirmed — `from datetime import datetime` (was `from datetime import datetime, timedelta`). No new code review findings introduced by this single-line change.

### UI Review
No UI-scope changes.

### AWS Review
No AWS changes in this diff.

### Security Review
Unchanged from prior report — INFO finding at `sync_job.py:L147-162` (osascript calendar-data string injection) remains deferred to backlog.

### Backlog Candidates
No new backlog candidates. All prior backlog items unchanged.

### Justification Review
Prior LOW finding L1 is FIXED — no justification required.

INFO findings I1–I4 from prior report assessed for this iteration:

- Finding: INFO: `sync_job.py:L181`: `from datetime import datetime as _dt` inside for-loop body
  - Implementer justification summary: none in decision.md
  - QA decision: accepted
  - QA analysis: Python caches module imports after first resolution; no performance impact. The pattern is unconventional but not incorrect and not flagged by ruff. Style nit only; does not affect correctness or security.
  - Reviewer context: acceptable for current codebase style. Revisit trigger: if a linter enforcing C0415 (imports-not-at-top) is added to CI.

- Finding: INFO: `sync_job.py:~L152`: f-string without placeholder in implicit string concatenation block
  - Implementer justification summary: none in decision.md
  - QA decision: accepted (finding downgraded to resolved-non-issue)
  - QA analysis: `uv tool run ruff` does not flag this line as F541 in the current run. Ruff's implicit-concatenation handling recognises that adjacent f-strings share interpolation scope and does not treat the partially-plain segment as a standalone F541 violation. Prior report finding was based on code inspection; the authoritative lint tool does not surface it. No action required.

- Finding: INFO: alarm recalculation in `_prompt_unknown_locations` omits existing fixed prep
  - Implementer justification summary: none in decision.md
  - QA decision: accepted
  - QA analysis: Unknown-location personal events fall back to Home=0 travel, so existing prep = 0. Simplification is equivalent for current use case. Revisit trigger: if a personal event can have meeting_type-based prep AND an unknown location simultaneously.

- Finding: INFO: `tests/test_sync_job.py` MOCK_POPUP_RESPONSE missing `location_travel_minutes` key — pre-existing mock drift
  - Implementer justification summary: none in decision.md
  - QA decision: accepted
  - QA analysis: `run_nightly_sync()` accesses this key via `.get()`; no crash or incorrect behaviour. Pre-existing pattern consistent with rest of file.

### Human Review Queue
(empty)

### QA Loop Decision
- PASS
- The single LOW finding from the prior iteration — unused `timedelta` import at `tests/test_sync_job.py:L236` — is confirmed fixed. No HIGH or MEDIUM findings exist. All INFO findings accepted (see Justification Review). Lint PASS (diff-scope, 0 new findings). Unit tests 166/166.

### Issues

#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
(none — L1 fixed)

#### INFO
- I1: `sync_job.py:L181` — deferred `from datetime import datetime as _dt` inside for-loop body; accepted without fix.
- I3: Alarm recalculation omits existing fixed prep — design note; correct today; accepted.
- I4: MOCK_POPUP_RESPONSE pre-existing mock drift; accepted.

### Spec Review

#### AC Coverage
Unchanged from prior report — all 13 ACs remain covered. The fix does not touch production code.

#### Out-of-scope Changes
None. The fix removes `timedelta` from one import line in the test file only.

### Rune Review
Unchanged from prior report — no new rune violations introduced by the import-only fix.
