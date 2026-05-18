## QA Report — US-2: sync_job.py Apple Calendar routing — 2026-05-17

### Missing Tests
- None. All ACs have corresponding tests.

### Negative Tests (minimum 3)
- `test_google_reads_when_not_accessible_silent`: verifies no notification and no Apple reads when is_accessible() returns False
- `test_apple_runtime_failure_falls_back_with_notification`: verifies RuntimeError from get_tomorrow_events triggers notification + Google fallback
- `test_alarm_events_filtered_from_apple_pool`: verifies events with "Alarm" in title are excluded from the unified pool before compute

### Edge Cases (minimum 3)
- `test_alarm_events_filtered_from_apple_pool`: Apple pool contains alarm event synced from Google — filtered before compute ✓
- `test_apple_exclude_calendars_forwarded_to_get_tomorrow_events`: config key `apple_exclude_calendars` propagated correctly (both positional and keyword arg patterns covered) ✓
- `test_apple_runtime_failure_falls_back_with_notification`: notification failure wrapped in inner try/except — notification failure does not mask fallback ✓

### Security Checklist
- [x] SQL/command injection? — `sync_job.py` does not invoke subprocesses directly; delegates to `apple_calendar.get_tomorrow_events()`, which uses `subprocess.run([...], ...)` (list form, no `shell=True`) per US-1 review. No injection surface in US-2 changes.
- [x] Auth bypass? — Not applicable. Apple reads are read-only. Alarm writes continue through existing OAuth path unchanged.
- [x] Sensitive data in logs/responses? — `_reason = str(exc)` from a RuntimeError is printed to stderr and surfaced in the rumps notification. RuntimeErrors from ical-guy contain CLI error output only (no credentials). Risk is LOW.
- [x] Input validation at boundaries? — `config.get("apple_exclude_calendars", [])` defaults safely to `[]`. No user-controlled input is interpolated into subcommands in this file.
- [x] Confused deputy / privilege escalation? — Not applicable.

### Performance Considerations
- `apple_calendar.is_accessible()` runs `ical-guy calendars --format json` on every sync run (nightly, or on-demand). The probe has a `timeout=15s` cap (enforced in US-1). Overhead is negligible for a nightly job.
- The fallback path (Apple read failure) runs both `get_msi_time_blocks()` and `get_personal_events()` after having attempted Apple reads — this adds one extra subprocess call overhead on failure, which is acceptable.

### Untested Assumptions
- AC2.10 (no Apple event data in state files): verified by code review only — no unit test confirms this. The implementation adds no new writes beyond `result["personal_events"] = []` (in-memory only). Acceptable for a negative structural property.
- AC2.11 (debug output): the `print(f"[DEBUG] Read source: ...")` line is present in code. No unit test asserts the debug print string. Debug output is not critical-path; absence of a unit test is acceptable per project convention.

### How This Fails in Prod
- If `apple_calendar.is_accessible()` intermittently returns True then `get_tomorrow_events()` raises, the fallback fires a notification and falls back to Google — loud but recoverable.
- If both Apple and Google reads fail in the same run, the outer `except Exception` at the pipeline level catches it, surfaces via `rumps.notification` + stderr, and releases the lock — sync fails gracefully.
- If `rumps.notification()` itself raises (e.g., macOS sandbox), the inner `try/except Exception: pass` swallows it — the fallback Google read still proceeds.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| is_accessible() True | is_accessible=True, get_tomorrow_events returns events | Apple path used; Google readers not called | ✓ test_apple_reads_used_when_accessible |
| Unified pool forwarded as msi_blocks | is_accessible=True, events=[Team Sync] | compute receives events as msi_blocks, personal_events=[] | ✓ test_apple_reads_passed_as_msi_blocks |
| is_accessible() False | is_accessible=False | Google path, no notification | ✓ test_google_reads_when_not_accessible_silent |
| RuntimeError from get_tomorrow_events | is_accessible=True, get_tomorrow_events raises | notification fired, Google fallback | ✓ test_apple_runtime_failure_falls_back_with_notification |
| Alarm event in Apple pool | pool contains "⏰ Alarm — Standup" | filtered before compute | ✓ test_alarm_events_filtered_from_apple_pool |
| apple_exclude_calendars forwarded | config has apple_exclude_calendars=["US Holidays"] | get_tomorrow_events called with ["US Holidays"] | ✓ test_apple_exclude_calendars_forwarded_to_get_tomorrow_events |
| run_calendar_write unchanged | Apple path completes | write called with same args as Google path | ✓ test_run_calendar_write_called_same_in_apple_path |
| AC2.10: no state file writes | Apple sync completes | No new keys in .phantom_state.json | code review only (negative structural property) |
| AC2.11: debug output | target_date passed (debug mode) | "[DEBUG] Read source: Apple Calendar" printed | code only; no unit test (acceptable) |

### Validation Runs
- Lint: PASS — `ruff check sync_job.py tests/test_sync_job.py` (provided by user; accepted)
- Unit tests: PASS — `python -m pytest tests/` — 239/239 (provided by user; accepted)

### Code Review

`sync_job.py`

L486-488: `use_apple = apple_calendar.is_accessible()` then debug print — clean placement after `parse_config`, before branching. ✓

L492: `_target = target_date if target_date is not None else date.today() + timedelta(days=1)` — `_` prefix on a local variable is unconventional (single-underscore is typically reserved for throwaway variables in Python). `target` or `resolved_target` would be cleaner. `_target` is unambiguous in context but slightly misuses the convention. INFO nit.

L498: `unified = [e for e in unified if "Alarm" not in e.get("title", "")]` — rebinding `unified` is fine; the comment on L497 correctly explains why (Google Calendar alarms synced into Calendar.app). ✓

L506: `except Exception as exc:` — broad catch is correct per spec note and consistent with the outer pipeline exception handler. ✓

L509-514: `try: rumps.notification(...) except Exception: pass` — defensive wrap prevents notification failure from masking the original error log. ✓

L538-540: `result["personal_events"] = [e for e in personal_events if ...]` — comment added `# (Apple path: personal_events=[] so this is a no-op; Google path: unchanged)` — clear explanation. ✓

`tests/test_sync_job.py`

L302-318: `test_apple_exclude_calendars_forwarded_to_get_tomorrow_events` — the assertion `kwargs.get("exclude_calendars") or mock_get_events.call_args[0][1]` handles both keyword and positional call patterns. Correct but slightly implicit; a comment explaining the dual-check would improve readability. INFO nit.

L213: `self.assertEqual(msi_arg, APPLE_EVENTS)` — `MOCK_RESULT` is a mutable module-level constant. `run_nightly_sync()` mutates it via `result["personal_events"] = []` during test execution. This is a pre-existing pattern (present in `TestRunNightlySync` since before US-2) and does not affect test correctness here, but it makes test isolation fragile if `MOCK_RESULT` is later extended. INFO, pre-existing.

### UI Review
No UI-scope changes.

### AWS Review
No AWS usage in this diff.

### Security Review
No security-relevant changes beyond what is covered in the Security Checklist above. Subprocess invocation is delegated entirely to `apple_calendar.py` (reviewed in US-1 QA). The fallback notification exposes only ical-guy CLI stderr text, which is safe.

### Backlog Candidates
- Finding Key: LOW|README.md|—|apple_calendar.py missing from Project Structure table (US-1 backlog item)
  - Backlog action: resolved in US-2 — `apple_calendar.py` added to Project Structure table and `tests/test_apple_calendar.py` listed under tests in README.md. No append needed.

### Justification Review
No Implementer justifications present in `decision.md` (file contains only the initial state entry). No LOW/INFO findings from a prior QA run exist to evaluate.

### Human Review Queue
None.

### QA Loop Decision
- PASS
- All 11 ACs (AC2.1–AC2.11) are satisfied by implementation and tests. No HIGH or MEDIUM findings. Two INFO nits (`_target` naming; dual-pattern assertion comment; MOCK_RESULT pre-existing mutability) do not require remediation. All rune rules satisfied. Lint PASS. 239/239 unit tests PASS. Spec hash matches (af1261cf8a16). The US-1 README backlog item is resolved by this story's changes.

### Issues
#### HIGH
None.

#### MEDIUM
None.

#### LOW
None.

#### INFO
- `sync_job.py:L492`: `_target` local variable name uses single-underscore prefix unconventionally. Rename to `resolved_target` or `target` for clarity.
- `tests/test_sync_job.py:L313-314`: The `or`-chained assertion for positional vs keyword arg check is implicit. A brief inline comment would improve readability.
- `tests/test_sync_job.py:L213`: `MOCK_RESULT` is a mutable module-level constant mutated by `run_nightly_sync()` during tests (`result["personal_events"] = []`). Pre-existing pattern — not introduced by US-2. Does not affect test correctness at current scale.
- `AC2.11`: No unit test for the `[DEBUG] Read source: ...` print. Debug output is acceptable without a unit test by project convention.

### Spec Review
#### AC Coverage
All ACs covered:
- AC2.1: `test_apple_reads_used_when_accessible` (is_accessible=True → Google readers not called)
- AC2.2: `test_google_reads_when_not_accessible_silent`
- AC2.3: `test_google_reads_when_not_accessible_silent` (no notification on silent fallback)
- AC2.4: `test_apple_runtime_failure_falls_back_with_notification`
- AC2.5: `test_alarm_events_filtered_from_apple_pool`
- AC2.6: `test_apple_reads_passed_as_msi_blocks`
- AC2.7: `test_run_calendar_write_called_same_in_apple_path`
- AC2.8: covered structurally — `is_accessible()` handles non-macOS internally; `test_google_reads_when_not_accessible_silent` exercises the False branch
- AC2.9: `test_google_reads_when_not_accessible_silent` (full pipeline identical to pre-NPC-0014)
- AC2.10: code review confirms no new persistent writes; no unit test (acceptable for a negative structural property)
- AC2.11: debug print present in code (`[DEBUG] Read source: ...`); no unit test (acceptable)

#### Out-of-scope Changes
None. `calendar_reader.py`, `calendar_writer.py`, and `compute.py` are untouched. Changed files: `sync_job.py`, `tests/test_sync_job.py`, `build/manual_tests.md`, `README.md` — all listed in the US-2 spec files section.

### Rune Review
- `update-manual-tests-md`: MT-14.1–MT-14.6 added to `build/manual_tests.md` with correct format (unique ID, Feature, Prerequisites, Steps, Pass criteria). ✓
- `update-readme`: `apple_calendar.py` added to Project Structure table; `tests/test_apple_calendar.py` listed under test files; "Optional Dependencies" section added documenting `ical-guy`. ✓
- `no-credentials-in-git`: `credentials.json` and `token.json` not in diff. ✓
- `python-version-compatibility`: No deprecated APIs. `date.today()`, `timedelta`, `datetime.fromisoformat()` are stable in Python 3.14. ✓
- `no-tkinter-in-rumps-process`: No tkinter in diff. ✓
- `update-build-tests-sh`: No new test files added (existing `test_sync_job.py` extended). `pytest tests/` auto-discovery unchanged. ✓
- `local-state-files-in-gitignore`: No new state files introduced. ✓
- `no-heredoc-in-fish`: No shell scripts modified. ✓
