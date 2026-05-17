## Story Review Report — US-2: Surface Unknown Locations in Popup and Write to Drive Config — 2026-05-16T02:00:00

### Validation Runs
- Lint: PASS (diff-scope) — `uv tool run ruff check sync_job.py drive_config.py tests/test_sync_job.py` — 4 pre-existing findings remain (already backlog-deferred by QA in prior report; `sync_job.py:L365` F541, `tests/test_sync_job.py:L3,4,6` F401); 0 new findings in current diff. The `timedelta` F401 fix (was `tests/test_sync_job.py:L236`) is confirmed absent.
- Unit tests: PASS — `bash build/tests.sh` — 166/166 passed

## Story Review Findings

### Phase 1 — Preliminary

**State files**
- `progress.md` status: `Done`, phase: `QA` ✓
- `decision.md`: has initialization entry with spec hash and rationale ✓
- `spec_hash` in `progress.md` (`75972f8a557d`) matches `spec_hash` in `spec.md` front matter ✓

No source-code issues found in this phase.

### Phase 2 — Spec Review

**Acceptance criteria**

| AC | Status | Notes |
|---|---|---|
| 2.1 | ✓ | `_show_popup` calls `_prompt_unknown_locations` when `unknown_personal_locations` non-empty and not baseline |
| 2.2 | ✓ | Groups by location string; one dialog per unique location |
| 2.3 | ✓ (simplified) | `candidate_alarm = event_start - timedelta(minutes=travel_minutes)`; equivalent for current use case (unknown-location personal events have 0 existing fixed prep) |
| 2.4 | ✓ | Only non-zero integers included in result dict |
| 2.5 | ✓ | `location_travel_minutes` present in all return paths of `_show_popup` |
| 2.6 | ✓ | Placed after `append_recurring_meetings` block in `run_nightly_sync` |
| 2.7 | ✓ | `{**location_travel_minutes, **existing_locations}` — existing entries take precedence; test confirmed |
| 2.8 | ✓ | try/except wraps `append_locations`; failure logs to stderr; calendar write unaffected |
| 2.9 | ✓ | Empty list returns `({}, alarm)`; `_prompt_unknown_locations` not called |
| 2.10 | ✓ | `travel_minutes <= 0` guard + blank check |
| 2.11 | ✓ | rc != 0 → `continue` (no crash, no write) |
| 2.12 | ✓ | All 4 `_show_popup` return paths include `location_travel_minutes` key |
| 2.13 | ✓ | 20 new tests in 4 test classes covering 2.4–2.11 |

**Scope check**
No changed file or behaviour outside ACs or decision.md rationale detected. All changed lines traceable to US-2 ACs.

**QA rules**
- QA remained review-only — no production/test/state edits ✓
- No tests deleted or relaxed ✓
- No HIGH findings from QA ✓
- No MEDIUM findings from QA ✓
- LOW finding L1 (`timedelta` unused import at `tests/test_sync_job.py:L236`): **FIXED** — confirmed removed; now `from datetime import datetime` only ✓
- INFO findings I1–I4: all accepted by QA with justification (see Justification Review below) ✓

### Phase 3 — Review Core

#### Rune Review

Diff checked against `docs/runes/phantom-calendar.md` (RUNE_STORE=filesystem) and global runes at `/Users/duybui/code/ai/local-tests/instructions/`.

**Component rune checks:**
- `update-build-tests-sh`: No new test files, no structural change to `tests/` — auto-discovery unchanged. ✓
- `update-manual-tests-md`: No manual ACs in US-2. ✓
- `update-readme`: No new runtime dependencies, no new source files, no new `build/manual_tests.md` sections. ✓
- `no-credentials-in-git`: `credentials.json` and `token.json` absent from diff. ✓
- `python-version-compatibility`: `datetime.fromisoformat()` (Python 3.7+); no deprecated APIs. ✓
- `venv-and-uv-conventions`: No bare `python`/`python3`/`pip` in diff. ✓
- `no-tkinter-in-rumps-process`: Uses osascript throughout for all UI. ✓
- `local-state-files-in-gitignore`: No new state or cache files introduced. ✓
- `icon-design-consistency`: Not applicable — no new icon states. ✓

**Global rune checks (python.instructions.md):**

Finding SR-G1 (INFO): `sync_job.py:L402-407` — `print()` used for status/warning output. Global rune prefers `logging` over `print`. Pre-existing pattern throughout `sync_job.py`; consistent with surrounding code; no `logging` module configured in this file.
→ Accepted (see Justification Review).

Finding SR-G2 (INFO): `sync_job.py:L124,141` — parameter `unknown_locs` and loop variable `loc` are abbreviated. Global rune prefers full words (e.g. `unknown_locations`, `location`). Spec implementation notes define the parameter as `unknown_locs`; `loc` is a short-lived intermediate.
→ Accepted (see Justification Review).

No rune violations requiring Implementer action.

**Rune Update Summary:** No rune updates required. All rules satisfied or explicitly accepted at INFO level.

#### Code Review

No new code-review findings beyond what QA already surfaced.

**Logic and correctness:**
- `append_locations`: `{**location_travel_minutes, **existing_locations}` correctly implements "existing not overwritten" — existing keys in `existing_locations` overwrite the same key from `location_travel_minutes`. Confirmed by `test_existing_location_not_overwritten`. ✓
- `_prompt_unknown_locations`: grouping by location, int validation, `<= 0` guard, rc check, and alarm recalculation logic all correct. ✓
- `_show_popup`: `location_travel_minutes` initialized before both classification and location-prompt branches; all 4 return paths include it. ✓
- `run_nightly_sync`: `append_locations` called only when `popup_response.get("location_travel_minutes")` is truthy (non-empty dict); guarded by try/except; does not affect calendar write path. ✓

**Test value:**
- All 20 new tests have non-trivial assertions covering distinct behaviours.
- `test_append_locations_failure_non_fatal` verifies both the non-raise and the calendar write still happened — good dual assertion.
- Negative tests: 6 explicit negatives (zero, blank, non-integer, rc≠0, empty list, Drive failure). ✓

No new code-review findings. QA INFO items I1–I4 carried forward as accepted.

#### UI Review
No UI-scope changes.

#### AWS Review
No AWS-scope changes.

#### Security Review

Finding SR-S1 (INFO): `sync_job.py:L147-162` — same osascript string injection finding from QA (carried forward). Calendar `location` and `title` strings interpolated directly into AppleScript `"..."` boundaries without escaping `"` characters. Worst case: dialog fails (rc≠0), location silently skipped. No external attack surface.
→ Accepted (see Justification Review). Consistent with existing `_classify_unknown_blocks` pattern.

No CRITICAL or HIGH security findings.

### UI Review
No UI-scope changes.

### Justification Review

**Finding SR-G1 — INFO: `sync_job.py:L402-407` — `print()` instead of `logging`**
- Prior-step context: Not flagged by QA. Story-Review surfaced from global rune `python.instructions.md` (`applyTo: **/*.py`).
- Story-Review decision: accepted
- Story-Review analysis: The entire `sync_job.py` file uses `print()` for status output (established pre-NPC-0012 pattern). No `logging` module is configured. Switching one block while the rest of the file uses `print()` would be inconsistent without a larger refactor. The risk of an inconsistent approach outweighs the style benefit of a partial fix. This is a systemic codebase issue, not a US-2-specific regression.
- Propagation: guardrails — if a future story introduces `logging` configuration to `sync_job.py`, all `print()` calls should be migrated. Revisit trigger: any story that imports the `logging` module into `sync_job.py`.

**Finding SR-G2 — INFO: `sync_job.py:L124,141` — abbreviated parameter `unknown_locs` / variable `loc`**
- Prior-step context: Not flagged by QA. Story-Review surfaced from global rune `python.instructions.md`.
- Story-Review decision: accepted
- Story-Review analysis: The spec implementation notes (`docs/NPC-0012/spec.md`) explicitly define the parameter signature as `unknown_locs: list`. The function name `_prompt_unknown_locations` already conveys the domain context fully; `unknown_locs` as a short parameter name is comprehensible to any reader who sees the function name. `loc` as a loop variable for `entry["location"]` in a 2-line inner scope is similarly low-risk. Renaming now would diverge from the approved spec signature with no functional benefit.
- Propagation: guardrails — future functions in this file should prefer full words unless the spec defines the abbreviation. Revisit trigger: if a linter enforcing naming conventions (e.g., pylint `C0103`) is added to CI.

**Finding QA-I1 — INFO: `sync_job.py:L181` — deferred `from datetime import datetime as _dt` inside for-loop body**
- Prior-step context: QA accepted — Python caches imports; no perf impact; ruff does not flag it; style nit only.
- Story-Review decision: accepted
- Story-Review analysis: QA's reasoning is correct and sufficient. The import is cached after first resolution; the function-level `from datetime import timedelta` at L136 (top of the same function) sets the pattern. No correctness or performance risk.
- Propagation: guardrails — new code in this file should use module-level imports. Revisit trigger: if `pylint C0415` (imports-not-at-top) is added to CI.

**Finding QA-I3 — INFO: alarm recalculation in `_prompt_unknown_locations` omits existing fixed prep**
- Prior-step context: QA accepted — unknown-location personal events fall back to `Home=0` travel, so existing prep = 0; simplification is equivalent for the current use case.
- Story-Review decision: accepted
- Story-Review analysis: QA's analysis is correct and bounded. AC 2.3 says "if the event is the first meeting (earliest start), `alarm_time = event["start"] - timedelta(minutes=entered_travel + existing_fixed)`" — the simplification drops `existing_fixed`, which is 0 by definition for the affected events. The implementation is functionally equivalent today.
- Propagation: guardrails — if a personal event can ever have meeting-type-based prep AND an unknown location simultaneously, this simplification becomes wrong. Revisit trigger: if `compute_alarm()` returns non-zero `prep_minutes` for a personal event that also has an unknown location entry.

**Finding QA-I4 — INFO: `tests/test_sync_job.py` MOCK_POPUP_RESPONSE missing `location_travel_minutes` key (pre-existing mock drift)**
- Prior-step context: QA accepted — `run_nightly_sync()` accesses via `.get()`; no crash or incorrect behaviour; pre-existing pattern.
- Story-Review decision: accepted
- Story-Review analysis: `.get()` with no default returns `None`, which is falsy; the `if popup_response.get("location_travel_minutes"):` guard in `run_nightly_sync` handles it correctly. Pre-existing pattern consistent with rest of file. No functional risk.
- Propagation: guardrails — new tests that add popup response mocks should include `location_travel_minutes` to stay current with the real return shape. Revisit trigger: if MOCK_POPUP_RESPONSE is used in a test that exercises `location_travel_minutes` logic directly.

**Finding SR-S1 — INFO: `sync_job.py:L147-162` — osascript string injection (calendar data)**
- Prior-step context: QA accepted as INFO — local app with trusted calendar data; graceful failure on dialog error; consistent with existing `_classify_unknown_blocks` pattern; deferred to backlog.
- Story-Review decision: accepted
- Story-Review analysis: QA's analysis is complete. This is a local-only app with no external network attack surface. The input source is the user's own Google Calendar `location` field — trusted but uncontrolled. Worst case is a silent skip (rc≠0 → `continue`), not a crash or data corruption. The identical pattern exists in `_classify_unknown_blocks` and has not caused issues. The risk is bounded by the app's deployment model.
- Propagation: guardrails — the backlog item (`INFO|phantom-calendar/sync_job.py|147|osascript-string-injection-calendar-data`) captures the required hardening step (`str.replace('"', '\\"')`). Revisit trigger: if the app is ever run with externally-sourced calendar data, or if a future story modifies the osascript construction in `_prompt_unknown_locations` or `_classify_unknown_blocks`.

### Backlog Candidates
No new backlog candidates identified in this Story-Review run. All prior QA backlog items (`sync_job.py:L365` F541, `tests/test_sync_job.py:L3,4,6` F401, `sync_job.py:L147-162` osascript injection) remain in `docs/NPC-0012/backlog.md` as previously appended. No new `Finding Key` values to add.

## Story Review Decision
- PASS
- No HIGH or MEDIUM findings in any phase. All LOW findings from QA resolved (L1 fixed). All INFO findings accepted at Story-Review with reasoning recorded. Lint PASS (diff-scope, 0 new findings). Unit tests 166/166. spec_hash verified. State files valid. Two-strike rule: first Story-Review run — no repeat findings possible.
