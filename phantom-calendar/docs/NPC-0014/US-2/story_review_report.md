## Story Review Report — US-2: sync_job.py Apple Calendar routing — 2026-05-17

### Validation Runs
- Lint: PASS — `ruff check sync_job.py tests/test_sync_job.py` — All checks passed
- Unit tests: PASS — `python -m pytest tests/ -q` — 239/239 passed in 1.52s

## Story Review Findings

### Phase 1 — Preliminary

State files:
- `progress.md` status: Done; phase: QA ✓
- `decision.md`: Initial state entry only (no Implementer justifications needed — no LOW/INFO findings from a prior QA run required remediation) ✓
- `spec_hash` in `progress.md` (`af1261cf8a16`) matches `spec_hash` in `spec.md` front matter (`af1261cf8a16`) ✓

### Phase 2 — Spec

AC Coverage:
- AC2.1: `test_apple_reads_used_when_accessible` + `test_apple_exclude_calendars_forwarded_to_get_tomorrow_events` ✓
- AC2.2: `test_google_reads_when_not_accessible_silent` ✓
- AC2.3: `test_google_reads_when_not_accessible_silent` (no notification on silent False) ✓
- AC2.4: `test_apple_runtime_failure_falls_back_with_notification` ✓
- AC2.5: `test_alarm_events_filtered_from_apple_pool` ✓
- AC2.6: `test_apple_reads_passed_as_msi_blocks` ✓
- AC2.7: `test_run_calendar_write_called_same_in_apple_path` ✓
- AC2.8: Structural — `is_accessible()` handles non-macOS internally; `test_google_reads_when_not_accessible_silent` exercises the False branch ✓
- AC2.9: `test_google_reads_when_not_accessible_silent` — full Google pipeline verified ✓
- AC2.10: Code review confirms no new persistent writes — acceptable negative structural property, no unit test required ✓
- AC2.11: `[DEBUG] Read source: ...` print present in code; no unit test per project convention ✓

Scope check: Changed files (`sync_job.py`, `tests/test_sync_job.py`, `build/manual_tests.md`, `README.md`) match the US-2 spec files section exactly. `calendar_reader.py`, `calendar_writer.py`, `compute.py` untouched. ✓

QA rules:
- QA remained review-only — no production/test/state edits ✓
- No tests deleted or relaxed ✓
- No HIGH findings ✓
- No MEDIUM findings ✓
- All QA INFO findings have QA-accepted justification in `qa_report.md` ✓

### Phase 3 — Review Core

#### Rune Review

All phantom-calendar component rune rules satisfied:
- `update-manual-tests-md`: MT-14.1–MT-14.6 added with correct format (Feature, Prerequisites, Steps, Pass criteria; unique IDs) ✓
- `update-readme`: `apple_calendar.py` added to Project Structure table; `tests/test_apple_calendar.py` listed under tests; "Optional Dependencies" section added documenting `ical-guy` ✓
- `no-credentials-in-git`: `credentials.json` and `token.json` absent from diff ✓
- `python-version-compatibility`: No deprecated APIs; `date.today()`, `timedelta`, `datetime.fromisoformat()` stable in Python 3.14 ✓
- `no-tkinter-in-rumps-process`: No tkinter in diff ✓
- `update-build-tests-sh`: No new test files added; `pytest tests/` auto-discovery unchanged ✓
- `local-state-files-in-gitignore`: No new state files ✓
- `no-heredoc-in-fish`: No shell scripts modified ✓
- `osaurus-config-location` / `osaurus-openai-client`: Not applicable (no osaurus changes) ✓

Rune Update Summary: No rune updates required. All existing rules satisfied.

#### Code Review

`sync_job.py`:
- L10: `import apple_calendar` — correctly placed in the third-party/local import block ✓
- L486–488: `use_apple = apple_calendar.is_accessible()` + conditional debug print — clean placement after `parse_config()` and before read block ✓
- L490–500: Apple try-block: `_target` resolution, `get_tomorrow_events()` call, alarm filter, `msi_blocks` / `personal_events` assignment — correct per spec implementation notes ✓
- L493–495: Both args passed positionally to `get_tomorrow_events(_target, config.get("apple_exclude_calendars", []))` — matches spec intent; `apple_exclude_calendars` defaults safely to `[]` ✓
- L497–498: Alarm filter comment accurate — guards against Google Calendar alarms synced into Calendar.app ✓
- L506–515: `except Exception as exc` + inner `try/except` wrapping `rumps.notification` — broad catch is correct per spec note; defensive wrap prevents notification failure from masking the original error log ✓
- L516: `use_apple = False` after fallback — technically dead state at this point but improves readability ✓
- L539: Comment `# (Apple path: personal_events=[] so this is a no-op; Google path: unchanged)` — correct and helpful ✓
- Docstring at L434–458: Updated execution order and read source selection sections — accurate ✓

`tests/test_sync_job.py`:
- `MOCK_CONFIG_WITH_APPLE` and `APPLE_EVENTS` module-level constants — sensible, consistent with existing test file style ✓
- `TestRunNightlySyncAppleCalendarRouting.setUp()` — releases lock if stuck, consistent with other test classes ✓
- 7 test methods covering AC2.1–AC2.9 (where unit-testable) ✓
- `test_google_reads_when_not_accessible_silent`: `rumps` patched inside body via context manager — correct; asserts `notification` not called ✓
- `test_apple_runtime_failure_falls_back_with_notification`: asserts notification message contains `"ical-guy crashed"` and `"Google Calendar"` — precise coverage ✓

INFO nits (no action required; all pre-identified by QA):
- INFO: `sync_job.py:L492` — `_target` single-underscore prefix; discussed in Justification Review below
- INFO: `tests/test_sync_job.py:L312` — `or`-chained assertion; discussed in Justification Review below
- INFO: `tests/test_sync_job.py:L213` — `MOCK_RESULT` pre-existing mutability; discussed in Justification Review below
- INFO: `AC2.11` — no unit test for debug print; discussed in Justification Review below

New Story-Review INFO (global Python instruction):
- INFO: `sync_job.py` — Multiple `print()` calls added (L488, L502–505, L508, L520) where the global `python.instructions.md` prefers `logging` over `print`. However, `sync_job.py` already contains dozens of `print()` calls throughout (pre-NPC-0014 established pattern). US-2 adds prints consistent with that style. Refactoring to `logging` is out of scope for this story. Classified as backlog candidate. See **Backlog Candidates** below.

`README.md` and `build/manual_tests.md`: No code review issues. MT-14.5 manual test describes a race condition step that is acknowledged as inherently difficult to reproduce mechanically — the pass criteria are clear and the test documents intent adequately.

#### UI Review
No UI-scope changes.

#### AWS Review
No AWS usage in this diff.

#### Security Review
- No subprocess invocations in US-2 changes — all subprocess calls delegated to `apple_calendar.get_tomorrow_events()` (reviewed in US-1 QA; uses list form, no `shell=True`)
- `_reason = str(exc)` notification message: contains RuntimeError text from `apple_calendar.get_tomorrow_events()` only (ical-guy CLI stderr output, no credentials). LOW risk, per QA security checklist ✓
- No new persistent state writes; `result["personal_events"] = []` is in-memory only ✓
- `config.get("apple_exclude_calendars", [])` — safe default at call site ✓

### Justification Review

- Finding: INFO: `sync_job.py:L492`: `_target` local variable uses single-underscore prefix unconventionally
  - Prior-step context: QA identified as INFO — "unambiguous in context but slightly misuses the convention"; QA decision: PASS without remediation required
  - Story-Review decision: accepted
  - Story-Review analysis: `_target` is assigned on L492 and consumed on L493 (one line later), inside a tightly scoped try-block. The intent is unambiguous. No behavioral risk. The single-underscore does not break any rune rule or project convention. Python's underscore convention is advisory, not mandatory.
  - Propagation: Guardrail — if `_target` is referenced in expanded logic (more lines between assignment and use) in a future story, rename to `resolved_target` for clarity. Revisit trigger: any story that extends the Apple try-block with additional branching logic.

- Finding: INFO: `tests/test_sync_job.py:L312`: `or`-chained assertion for positional vs keyword arg implicit
  - Prior-step context: QA identified as INFO — "slightly implicit; a comment explaining the dual-check would improve readability"
  - Story-Review decision: accepted
  - Story-Review analysis: The production code calls `get_tomorrow_events(_target, config.get(...))` with both args positional. `kwargs.get("exclude_calendars")` returns `None`, so the `or` falls through to `mock_get_events.call_args[0][1]` — the second positional arg — which is `["US Holidays"]`. The assertion is correct. No behavioral risk. A comment would help but is not required for correctness.
  - Propagation: Guardrail — if the production call is ever changed to use keyword args, the `call_args[0][1]` branch breaks. Revisit trigger: any story that modifies the `get_tomorrow_events()` call signature or calling convention.

- Finding: INFO: `tests/test_sync_job.py:L213`: `MOCK_RESULT` mutable module-level constant mutated during test run
  - Prior-step context: QA identified as INFO — "pre-existing pattern — not introduced by US-2"; QA decision: PASS
  - Story-Review decision: accepted
  - Story-Review analysis: `run_nightly_sync()` mutates `MOCK_RESULT` via `result["personal_events"] = []`. This is pre-existing behavior from before NPC-0014. The new tests in `TestRunNightlySyncAppleCalendarRouting` assert `msi_arg == APPLE_EVENTS` (compute input), not `MOCK_RESULT`'s `personal_events` key, so no test in this class is affected by the mutation. No behavioral risk at current scale.
  - Propagation: Guardrail — if a future test in this class depends on `MOCK_RESULT["personal_events"]` being stable across runs, it will fail non-deterministically depending on test order. Revisit trigger: any `TestRunNightlySyncAppleCalendarRouting` test that asserts `MOCK_RESULT["personal_events"]` directly.

- Finding: INFO: `AC2.11`: No unit test for `[DEBUG] Read source: ...` print output
  - Prior-step context: QA accepted — "debug output acceptable without unit test by project convention"; MT-14.1 pass criteria mention checking `[sync_job] Read source: Apple Calendar` in stderr (manual coverage)
  - Story-Review decision: accepted
  - Story-Review analysis: Debug prints are guarded by `if debug:` and are not critical-path. The print is present in the diff (L488). Manual test MT-14.1 documents the expected stderr string for human verification. No behavioral risk.
  - Propagation: Guardrail — if debug output becomes a contracted API (e.g., parsed by external tooling or a test harness), a unit test is required. Revisit trigger: any story that introduces programmatic consumption of `[DEBUG]` output.

### Backlog Candidates

- Finding Key: INFO|sync_job.py|multiple|print() used where global python.instructions.md prefers logging
  - Finding: INFO: `sync_job.py` L488/L502–505/L508/L520 — new `print()` calls added; global `python.instructions.md` Rule says "prefer `logging` over `print`"
  - Why deferred: pre-existing project-wide pattern throughout `sync_job.py` (dozens of print calls predating NPC-0014); refactoring the entire file to `logging` is out of scope for this routing story
  - Suggested next action: new story — "Migrate sync_job.py debug/error output from print() to logging module (per python.instructions.md global rule)"
  - Backlog action: appended to `docs/NPC-0014/backlog.md`

## Story Review Decision
- PASS
- All 11 ACs (AC2.1–AC2.11) verified by implementation and tests. Lint PASS. 239/239 unit tests PASS. spec_hash matches (af1261cf8a16). No HIGH or MEDIUM findings from any review phase. Four QA INFO findings accepted with Story-Review reasoning and propagation guardrails recorded. One new INFO backlog candidate identified (print vs logging pre-existing pattern) — classified as backlog, not blocking. All rune rules satisfied. No out-of-scope changes.
