## Feature Review Iteration 1 — 2026-05-17

### Validation
- ruff check (NPC-0014-touched files: `apple_calendar.py`, `drive_config.py`, `sync_job.py`, `tests/test_apple_calendar.py`, `tests/test_drive_config.py`, `tests/test_sync_job.py`) — PASS
  - Note: pre-existing E402/F401 errors in `app.py` are out of scope for NPC-0014.
- pytest `tests/` — 239/239 PASS

### Code Review

All NPC-0014 source changes reviewed against spec and prior-step reports.

`apple_calendar.py`:
- `_ical_guy_path()` probes known Homebrew prefix paths when PATH is restricted (launchd/Finder launch). Correct — prevents silent inaccessible on macOS app bundle launches.
- `is_accessible()` short-circuits cleanly (platform → version → binary → probe → JSON parse). All failure modes return False. Wrapped in broad `try/except` per spec. ✓
- `get_tomorrow_events()` uses `subprocess.run([...], capture_output=True, text=True, timeout=15)` — list form, no `shell=True`, no injection surface. ✓
- Timezone conversion applied in local time before date-filter: correct edge-case handling for near-midnight UTC events. ✓
- `endDate` absent/malformed → `end_dt = start_dt` fallback. ✓
- All INFO findings from US-1 QA and Story-Review were remediated before Story-Review PASS. ✓

`drive_config.py`:
- `_DEFAULTS["apple_exclude_calendars"] = []` present. ✓
- `_parse_apple_exclude()` returns `[]` on missing key and non-list value. ✓
- No changes to write paths — `append_recurring_meetings()` and `append_locations()` unchanged. ✓

`sync_job.py`:
- `import apple_calendar` correctly placed in the local import block. ✓
- `use_apple = apple_calendar.is_accessible()` called once after `parse_config()`. ✓
- `timezone_str` forwarded as third positional arg to `get_tomorrow_events()` — correct (spec implementation notes showed 2 args but code correctly passes 3 to use the configured timezone). ✓
- Alarm filter `"Alarm" not in e.get("title", "")` applied to unified pool. ✓
- Fallback: `rumps.notification()` wrapped in inner `try/except` — notification failure cannot suppress the Google Calendar fallback. ✓
- `personal_events = []` assigned for Apple path — `result["personal_events"]` assignment on L539 is a no-op for Apple runs. ✓

**Bugfix applied this session (not a spec story — pre-existing bug):**
- `sync_job.py` L591: removed `popup_response.get("confirmed")` gate from the classifications save block.
- Bug: on baseline days (most weekday mornings), `_show_popup()` returns `confirmed=False` because no calendar write is needed. The old gate discarded all "Recurring" classification answers silently — user was asked about the same unknown meeting every run.
- Fix: save `classifications` unconditionally when non-empty. Users already expressed explicit "Recurring" intent in the dialog; that intent should not depend on whether a calendar write occurred.
- The fix is minimal and correct. No security implications. No spec AC is violated — the original spec for NPC-0007 US-2 (AC2.3) requires writing classifications after `run_calendar_write()` when confirmed; the bugfix relaxes "and confirmed" to "classifications non-empty" since the Recurring choice is independent of the alarm write decision. ✓

### UI Review
No UI-scope changes.

### AWS Review
No AWS usage in this diff.

### Security Review
- `subprocess.run([...], capture_output=True, text=True, timeout=15)` — list form throughout. No shell injection surface. ✓
- `exclude_calendars` joined with commas and passed as a single arg value. Comma in a calendar name could split incorrectly — limitation of ical-guy CLI design, not an injection risk. Documented in US-1 QA "How This Fails in Prod". ✓
- `rumps.notification()` message contains only RuntimeError text from ical-guy stderr output. No credentials. ✓
- No new persistent state writes. Apple Calendar event data not stored in any state file. ✓
- `credentials.json` and `token.json` absent from diff. ✓

### Rune Review

All phantom-calendar component rune rules satisfied:
- `update-build-tests-sh`: `pytest tests/` auto-discovers `test_apple_calendar.py`; no structural layout change. ✓
- `update-manual-tests-md`: MT-14.1–MT-14.6 added in US-2. ✓
- `update-readme`: `apple_calendar.py` added to Project Structure table; `tests/test_apple_calendar.py` listed under tests; "Optional Dependencies" section added for ical-guy — backlog item from US-1 resolved in US-2. ✓
- `no-credentials-in-git`: absent from diff. ✓
- `python-version-compatibility`: No deprecated APIs; `datetime.fromisoformat()`, `date.today()`, `timedelta` stable in Python 3.14. ✓
- `no-tkinter-in-rumps-process`: No tkinter in diff. ✓
- `osaurus-*` rules: Not applicable (apple_calendar.py does not use osaurus). ✓
- `local-state-files-in-gitignore`: No new state files. ✓
- `no-heredoc-in-fish`: Not applicable. ✓

Rune Update Summary: No rune file updates required.

### Justification Review

- Finding: INFO: `sync_job.py:L492`: `_target` local variable uses single-underscore prefix
  - Prior-step context: QA INFO — "unambiguous in context, slightly misuses convention"; QA decision: PASS. Story-Review accepted — assigned and consumed within the same 1-line span inside a tightly scoped try-block.
  - Feature-Review decision: accepted
  - Feature-Review analysis: No behavioral risk. Assignment and consumption are adjacent. No rune violation.
  - Propagation: if any future story expands the Apple try-block with additional branching between assignment and use of `_target`, rename to `resolved_target`. Revisit trigger: any story that extends the Apple Calendar try-block in `run_nightly_sync()`.

- Finding: INFO: `sync_job.py` multiple lines — `print()` calls added where `python.instructions.md` prefers `logging`
  - Prior-step context: Story-Review identified as backlog candidate — pre-existing pattern throughout `sync_job.py` (dozens of print calls predating NPC-0014); Story-Review decision: deferred to backlog.
  - Feature-Review decision: accepted (deferred to backlog)
  - Feature-Review analysis: The new print calls are consistent with the pre-existing codebase style. Migrating a single story's additions to `logging` while the rest of the file uses `print` would create inconsistency worse than the violation itself. A full-file migration is the correct fix and must be its own story.
  - Propagation: `INFO|sync_job.py|multiple|print() over logging` appended to `docs/backlog.md`. Revisit trigger: any story that introduces structured log analysis or a dedicated logging subsystem.

- Finding: INFO: `tests/test_sync_job.py:L312` — `or`-chained assertion for positional vs keyword arg
  - Prior-step context: QA INFO. Story-Review accepted — assertion is correct; `call_args[0][1]` branch covers positional call pattern.
  - Feature-Review decision: accepted
  - Feature-Review analysis: No correctness risk at current call site. Code passes timezone_str as third positional arg; the assertion handles both positional and keyword patterns robustly.
  - Propagation: if `get_tomorrow_events()` call signature changes to use keyword args, the `call_args[0][1]` branch breaks. Revisit trigger: any story that modifies the `get_tomorrow_events()` call.

- Finding: INFO: `tests/test_sync_job.py:L213` — `MOCK_RESULT` mutable module-level constant
  - Prior-step context: QA INFO — pre-existing pattern; Story-Review accepted with guardrail.
  - Feature-Review decision: accepted
  - Feature-Review analysis: No test in `TestRunNightlySyncAppleCalendarRouting` depends on `MOCK_RESULT["personal_events"]`. Mutation affects in-memory dict only.
  - Propagation: guardrail stands — if a future Apple-path test asserts `MOCK_RESULT["personal_events"]` directly, the test will be non-deterministically order-dependent. Revisit trigger: any future Apple-path test that reads `MOCK_RESULT["personal_events"]`.

- Finding: INFO: `AC2.11` — no unit test for `[DEBUG] Read source: ...` debug print
  - Prior-step context: QA + Story-Review accepted — debug output is not critical-path; MT-14.1 covers manual verification.
  - Feature-Review decision: accepted
  - Feature-Review analysis: No functional risk.
  - Propagation: if debug output becomes a contracted API (parsed by tooling), add a unit test. Revisit trigger: any story that programmatically consumes `[DEBUG]` output.

### Backlog Review
- Existing backlog entries reviewed: 1 (in `docs/NPC-0014/backlog.md`)
- Unresolved backlog items that need triage now: none
- Existing backlog items resolved this run:
  - `LOW|README.md|—|apple_calendar.py missing from Project Structure table` — resolved in US-2 (README.md updated with apple_calendar.py, tests/test_apple_calendar.py, and Optional Dependencies section)
- New backlog entries appended this run (to `docs/backlog.md`):
  - `INFO|sync_job.py|multiple|print() used where logging is preferred (global python.instructions.md rule)` — deferred; full-file migration is the correct scope

### External Feedback Intake
- Source: human-test (reported on NPC-0014 branch, 2026-05-17)
  - Finding: MEDIUM: `sync_job.py:~L591`: Recurring classifications discarded on baseline days — "Pod Tech Leads Standup - Polara" asked every run
  - Evidence: User confirmed repeated classification dialog for the same meeting across multiple runs on NPC-0014 branch
  - Feature-Review disposition: needs-rework
  - Required remediation: Remove `popup_response.get("confirmed")` gate from the classifications save block. Applied inline this session. Verified working by user.
  - Status: RESOLVED — bugfix committed to NPC-0014 branch

### Accepted Findings and Justifications
<!-- Copy this section verbatim into the child PR description. -->
- Finding Key: INFO|sync_job.py|L492|_target single-underscore prefix
  - Decision chain:
    - QA: accepted — unambiguous in context; advisory convention only
    - Story-Review: accepted — assignment and consumption within 1-line span
    - Feature-Review: accepted — no rune violation; no behavioral risk
  - Final status for PR context: accepted
  - Guardrails and revisit trigger: rename to `resolved_target` if Apple try-block expands with additional branching between assignment and use

- Finding Key: INFO|sync_job.py|multiple|print() over logging (global rule)
  - Decision chain:
    - Story-Review: deferred to backlog — pre-existing pattern; single-story migration creates inconsistency
    - Feature-Review: accepted — full-file migration is the correct scope; appended to global backlog
  - Final status for PR context: accepted
  - Guardrails and revisit trigger: revisit when a logging subsystem story is planned

- Finding Key: INFO|tests/test_sync_job.py|L312|or-chained assertion for positional/keyword arg
  - Decision chain:
    - QA: accepted — correct for current call site
    - Story-Review: accepted — guardrail documented
    - Feature-Review: accepted — assertion is robust for current 3-arg positional call
  - Final status for PR context: accepted
  - Guardrails and revisit trigger: if `get_tomorrow_events()` call convention changes to keyword args, update assertion

- Finding Key: INFO|tests/test_sync_job.py|L213|MOCK_RESULT mutable module-level constant
  - Decision chain:
    - QA: accepted — pre-existing pattern
    - Story-Review: accepted — no new tests depend on `personal_events` value
    - Feature-Review: accepted — no current risk
  - Final status for PR context: accepted
  - Guardrails and revisit trigger: if a future Apple-path test reads `MOCK_RESULT["personal_events"]` directly, mutation ordering becomes fragile

- Finding Key: INFO|AC2.11|no unit test for debug print
  - Decision chain:
    - QA: accepted — debug output not critical-path; MT-14.1 covers manual verification
    - Story-Review: accepted
    - Feature-Review: accepted
  - Final status for PR context: accepted
  - Guardrails and revisit trigger: add unit test if debug output becomes a contracted API

### Summary
- Total findings: 0 HIGH, 0 MEDIUM (1 MEDIUM resolved inline as bugfix), 0 LOW, 5 INFO (all accepted)
- Decision: PASS
