## QA Report — US-1 Extend calendar readers to return title and description — 2026-05-17

### Missing Tests
- `test_get_personal_events_summary_absent_defaults_untitled` — AC1.4 requires coverage for summary absent → `"Untitled"` on personal events. The MSI equivalent (`test_get_msi_time_blocks_summary_absent_defaults_untitled`) exists but the personal events equivalent is missing.

### Negative Tests (minimum 3)
- `test_get_msi_time_blocks_summary_absent_defaults_untitled`: verifies title defaults to "Untitled" when API event has no summary key
- `test_get_msi_time_blocks_description_absent_defaults_empty`: verifies description defaults to "" when no description key
- `test_get_personal_events_description_absent_defaults_empty`: verifies description defaults to "" for personal events when absent

### Edge Cases (minimum 3)
- `test_get_msi_time_blocks_skips_all_day_events`: all-day events (no dateTime) are silently excluded
- `test_get_msi_time_blocks_empty_list`: empty API response returns empty list
- `test_get_personal_events_skips_all_day`: personal all-day events excluded
- Missing: personal event with empty-string summary (covered by `or "Untitled"` but no test)

### Security Checklist
- [x] SQL/command injection? — N/A, no SQL or shell commands in diff
- [x] Auth bypass? — N/A, no auth changes
- [x] Sensitive data in logs/responses? — No logging added; calendar data stays in returned dicts
- [x] Input validation at boundaries? — `or` operator handles falsy values (None, empty string) for title/description defaults
- [x] Confused deputy / privilege escalation? — N/A

### Performance Considerations
No concerns. Two string fields added to existing dict construction per event — negligible overhead.

### Untested Assumptions
- Empty-string summary from Google Calendar API is treated as absent (→ "Untitled") due to `or` operator. This is the intentional behavioral change but has no dedicated test.

### How This Fails in Prod
- If Google Calendar API returns a summary with a falsy but meaningful value (unlikely but theoretically possible), `or "Untitled"` would mask it. In practice, empty summaries from Google are indistinguishable from absent, so risk is negligible.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| MSI block with summary + description | event with both fields | title=summary, desc=description | ✅ test_get_msi_time_blocks_returns_expected_keys |
| MSI block no summary | event missing summary key | title="Untitled" | ✅ test_get_msi_time_blocks_summary_absent_defaults_untitled |
| MSI block no description | event missing description key | description="" | ✅ test_get_msi_time_blocks_description_absent_defaults_empty |
| Personal event with summary + description | event with both fields | title=summary, desc=description | ✅ test_get_personal_events_includes_title |
| Personal event no description | event missing description key | description="" | ✅ test_get_personal_events_description_absent_defaults_empty |
| Personal event no summary | event missing summary key | title="Untitled" | ❌ MISSING |
| All-day MSI event | date-only event | skipped | ✅ test_get_msi_time_blocks_skips_all_day_events |
| All-day personal event | date-only event | skipped | ✅ test_get_personal_events_skips_all_day |
| Empty event list | no items | [] | ✅ both empty_list tests |
| Sort order | multiple events | sorted by start ascending | ✅ test_get_msi_time_blocks_sorted_ascending |
| compute_alarm unaffected | existing test_compute.py | all pass | ✅ 169/169 |

### Validation Runs
- Lint: FAIL — `ruff check calendar_reader.py tests/test_calendar_reader.py` → 1 error: F401 unused import `MagicMock` in tests/test_calendar_reader.py:5
- Unit tests: PASS — `python -m pytest tests/ -v` → 169/169 passed in 0.41s

### Code Review
- `tests/test_calendar_reader.py`:L5: unused import `MagicMock`. remove it.
- `calendar_reader.py`:L97: behavioral change from `event.get("summary", "Untitled")` to `event.get("summary") or "Untitled"` in `get_personal_events()` — treats empty-string summary as absent. Intentional per progress.md but not documented in decision.md.

### UI Review
No UI-scope changes.

### AWS Review
No AWS-scope changes.

### Security Review
No security concerns. Changes are additive dictionary fields from trusted Google Calendar API responses. No user input, no shell commands, no logging of sensitive data.

### Backlog Candidates
None.

### Justification Review
- Finding: LOW: `calendar_reader.py`:L97: behavioral change from `event.get("summary", "Untitled")` to `event.get("summary") or "Untitled"` in `get_personal_events()`
  - Implementer justification summary: Consistency with MSI block handling — both now treat empty-string summaries as "Untitled". Previously, personal events kept empty string as title while MSI blocks defaulted to "Untitled".
  - QA decision: accepted
  - QA analysis: The change unifies behavior across both calendar reader functions. Empty-string summaries from Google Calendar API are semantically equivalent to absent summaries. The `or` pattern is idiomatic Python and matches the existing MSI block implementation. No downstream code depends on empty-string titles.
  - Reviewer context: If a future requirement needs to distinguish empty vs absent summaries, this `or` pattern must be revisited. Currently no such requirement exists.

### Human Review Queue
None.

### QA Loop Decision
- REWORK_REQUIRED
- MEDIUM: Missing test `test_get_personal_events_summary_absent_defaults_untitled` — AC1.4 requires coverage for summary absent → "Untitled" on both functions; personal events case is untested.
- LOW: Unused `MagicMock` import in tests/test_calendar_reader.py:5 (ruff F401). Fix or justify.
- LOW: Behavioral change (empty string summary → "Untitled" in personal events) not documented in decision.md. Add entry.

### Issues
#### HIGH
(none)

#### MEDIUM
- `tests/test_calendar_reader.py`: Missing `test_get_personal_events_summary_absent_defaults_untitled`. AC1.4 requires summary-absent tests for both `get_msi_time_blocks()` and `get_personal_events()`. Only the MSI variant exists. Add the personal events variant.

#### LOW
- `tests/test_calendar_reader.py`:L5: F401 unused import `MagicMock`. Remove the import.
- `decision.md`: Missing entry for the intentional behavioral change from `event.get("summary", "Untitled")` to `event.get("summary") or "Untitled"` in `get_personal_events()`. This changes behavior for empty-string summaries (now defaulting to "Untitled" instead of keeping ""). Document rationale in decision.md.

#### INFO
(none)

### Spec Review
#### AC Coverage
- AC1.1 ✅ — `get_msi_time_blocks()` returns `title` and `description` with documented defaults
- AC1.2 ✅ — `get_personal_events()` returns `description` defaulting to `""`
- AC1.3 ✅ — Existing test renamed and assertions updated; all 169 tests pass
- AC1.4 ❌ — Partially met. MSI block tests complete. Personal events missing summary-absent test.
- AC1.5 ✅ — `compute.py` not modified; `test_compute.py` passes

#### Out-of-scope Changes
- `get_personal_events()` title default changed from `event.get("summary", "Untitled")` to `event.get("summary") or "Untitled"` — minor behavioral change (empty string → "Untitled"). Consistent with MSI block behavior. Acceptable but needs decision.md entry.

### Rune Review
- `update-build-tests-sh`: No test files added/removed, only modified. `build/tests.sh` still discovers. ✅
- `update-manual-tests-md`: No manual ACs in US-1. ✅
- `no-credentials-in-git`: No credentials in diff. ✅
- `python-version-compatibility`: No deprecated APIs used. ✅
- `venv-and-uv-conventions`: N/A for code changes. ✅
- `no-tkinter-in-rumps-process`: N/A. ✅

---

## QA Report — US-1 Extend calendar readers to return title and description — Pass 2 — 2026-05-17

### Resolved Findings from Pass 1
1. ✅ MEDIUM: `test_get_personal_events_summary_absent_defaults_untitled` added (line 163). Asserts `title == "Untitled"` when event has no summary key. AC1.4 now fully covered.
2. ✅ LOW: Unused `MagicMock` import removed from `tests/test_calendar_reader.py:5`.
3. ✅ LOW: Behavioral change documented in `decision.md` — entry added for `event.get("summary") or "Untitled"` change in `get_personal_events()`.

### Missing Tests
None. All AC1.4 scenarios covered for both `get_msi_time_blocks()` and `get_personal_events()`.

### Negative Tests (minimum 3)
- `test_get_msi_time_blocks_summary_absent_defaults_untitled`: no summary key → "Untitled"
- `test_get_msi_time_blocks_description_absent_defaults_empty`: no description key → ""
- `test_get_personal_events_description_absent_defaults_empty`: no description → ""
- `test_get_personal_events_summary_absent_defaults_untitled`: no summary key → "Untitled"

### Edge Cases (minimum 3)
- `test_get_msi_time_blocks_skips_all_day_events`: all-day events silently excluded
- `test_get_msi_time_blocks_empty_list`: empty API response → empty list
- `test_get_personal_events_skips_all_day`: personal all-day events excluded

### Security Checklist
- [x] SQL/command injection? — N/A
- [x] Auth bypass? — N/A
- [x] Sensitive data in logs/responses? — No logging added
- [x] Input validation at boundaries? — `or` operator handles falsy values
- [x] Confused deputy / privilege escalation? — N/A

### Performance Considerations
No concerns. Two string fields per event dict — negligible.

### Untested Assumptions
- Empty-string summary treated as absent via `or` operator. Intentional, documented in `decision.md`. Risk: negligible (Google Calendar empty summaries are semantically absent).

### How This Fails in Prod
- Falsy but meaningful summary values would be masked by `or "Untitled"`. Practically impossible with Google Calendar API.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| MSI block with summary + description | event with both fields | title=summary, desc=description | ✅ |
| MSI block no summary | event missing summary key | title="Untitled" | ✅ |
| MSI block no description | event missing description key | description="" | ✅ |
| Personal event with summary + description | event with both fields | title=summary, desc=description | ✅ |
| Personal event no description | event missing description key | description="" | ✅ |
| Personal event no summary | event missing summary key | title="Untitled" | ✅ |
| All-day MSI event | date-only event | skipped | ✅ |
| All-day personal event | date-only event | skipped | ✅ |
| Empty event list | no items | [] | ✅ |
| Sort order | multiple events | sorted by start ascending | ✅ |
| compute_alarm unaffected | existing test_compute.py | all pass | ✅ |

### Validation Runs
- Lint: PASS — `ruff check calendar_reader.py tests/test_calendar_reader.py` → All checks passed
- Unit tests: PASS — `python -m pytest tests/ -v` → 170/170 passed in 0.40s

### Code Review
No new findings. All pass-1 code issues resolved.

### UI Review
No UI-scope changes.

### AWS Review
No AWS-scope changes.

### Security Review
No security concerns. Additive dict fields from trusted API responses.

### Backlog Candidates
None.

### Justification Review
- Finding: LOW: `calendar_reader.py`:L97: behavioral change from `event.get("summary", "Untitled")` to `event.get("summary") or "Untitled"` in `get_personal_events()`
  - Implementer justification summary: Consistency with MSI block handling — both now treat empty-string summaries as "Untitled". Previously, personal events kept empty string as title while MSI blocks defaulted to "Untitled".
  - QA decision: accepted
  - QA analysis: The change unifies behavior across both calendar reader functions. Empty-string summaries from Google Calendar API are semantically equivalent to absent summaries. The `or` pattern is idiomatic Python and matches the existing MSI block implementation. No downstream code depends on empty-string titles.
  - Reviewer context: If a future requirement needs to distinguish empty vs absent summaries, this `or` pattern must be revisited. Currently no such requirement exists.

### Human Review Queue
None.

### QA Loop Decision
PASS

All 3 findings from pass 1 resolved:

| Finding | Resolution |
|---------|------------|
| MEDIUM: Missing `test_get_personal_events_summary_absent_defaults_untitled` | ✅ Test added — verifies `title == "Untitled"` for events with no summary key |
| LOW: Unused `MagicMock` import | ✅ Removed from imports |
| LOW: Behavioral change undocumented in decision.md | ✅ decision.md entry added documenting the `or "Untitled"` change |

### Validation Runs
- Unit tests: PASS — `python -m pytest tests/ -v` → 170/170 passed
- All ACs (1.1–1.5) fully covered
- Scope limited to touch-list files
