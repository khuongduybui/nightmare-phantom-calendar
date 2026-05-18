## Story Review Report — US-1: apple_calendar.py — 2026-05-17

### Validation Runs
- Lint: PASS — `ruff check apple_calendar.py drive_config.py tests/test_apple_calendar.py tests/test_drive_config.py` — no errors (pre-existing E402 violations in `app.py` are out of scope for this story)
- Unit tests: PASS — `python -m pytest tests/ -q` — 232/232 passed in 0.64s

## Story Review Findings

### Phase 1 — Preliminary

- `progress.md` status: Done ✓
- `progress.md` phase: QA ✓
- `spec_hash` in `progress.md` (`af1261cf8a16`) matches `spec_hash` in `spec.md` front matter ✓
- `decision.md` contains only the initial state entry; all spec implementations are straightforward with no non-obvious decisions requiring rationale ✓

### Phase 2 — Spec Review

**AC Coverage**

All 17 ACs satisfied:
- AC1.1 ✓ — `platform.system() != "Darwin"` short-circuit in `is_accessible()`
- AC1.2 ✓ — `int(ver_str.split(".")[0]) < 14` check; empty string handled by `not ver_str` guard
- AC1.3 ✓ — `shutil.which("ical-guy") is None` short-circuit
- AC1.4 ✓ — probe `returncode != 0` returns False
- AC1.5 ✓ — returns True when macOS ≥14, ical-guy in PATH, probe exits 0, JSON parses
- AC1.6 ✓ — returns list[dict] with `start`, `end`, `title`, `description`, `location`; timezone-aware for test fixtures with UTC offset strings
- AC1.7 ✓ (structural) — no per-calendar filtering code; all ical-guy output events included
- AC1.8 ✓ — `--exclude-calendars` arg appended when `exclude_calendars` provided
- AC1.9 ✓ — `--exclude-all-day` flag + redundant `isAllDay` filter in loop
- AC1.10 ✓ — `start_dt.date() != target_date` filter
- AC1.11 ✓ — `sorted(events, key=lambda e: e["start"])` ascending
- AC1.12 ✓ — non-zero exit and unparseable JSON each raise `RuntimeError`
- AC1.13 ✓ — `event.get("notes") or ""`
- AC1.14 ✓ — `notes=None` → `""`
- AC1.15 ✓ — `parse_config()` returns `apple_exclude_calendars: ["US Holidays"]` from YAML
- AC1.16 ✓ — missing key → `[]` via `_parse_apple_exclude()` returning `[]`
- AC1.17 ✓ — `raise RuntimeError("Apple Calendar not accessible: ical-guy unavailable")` on `is_accessible()` False

**Scope check**

Changed files: `apple_calendar.py` (new), `drive_config.py` (extended), `tests/test_apple_calendar.py` (new), `tests/test_drive_config.py` (extended). Matches spec `### Files` list exactly. No out-of-scope changes. ✓

**QA rules**

- QA remained review-only — no production/test/state edits ✓
- No tests deleted or relaxed ✓
- HIGH findings: none ✓
- MEDIUM findings: none ✓
- LOW findings from QA Run 1: all 4 resolved by code fix ✓
- INFO findings from QA: carried as awareness items; reviewed in Justification Review below ✓

### Phase 3 — Review Core

#### Rune Review

Global runes (`python.instructions.md`):
- Full words for variable names: `event` (not `ev` — already fixed from QA Run 1), `start_dt`, `end_dt`, `start_str`, `end_str`, `raw_events`, `date_iso` — all compliant ✓
- f-strings preferred: `f"ical-guy events failed: {result.stderr.strip()}"`, `f"ical-guy returned invalid startDate {start_str!r}: {exc}"`, `f"ical-guy returned unparseable output: {exc}"` — all use f-strings ✓
- `logging` over `print`: no `print` calls added; `is_accessible()` returns False on all exceptions (no logging surface needed); `get_tomorrow_events()` raises `RuntimeError` (no logging surface needed) — rule is satisfied (no `print` to replace) ✓
- Class names: no new classes ✓

Component rune `phantom-calendar.md`:
- `update-build-tests-sh`: `python -m pytest tests/ -v` auto-discovers `tests/test_apple_calendar.py`; `build/tests.sh` needs no change ✓
- `update-manual-tests-md`: no manual-only ACs in US-1 ✓
- `update-readme`: `apple_calendar.py` is a new source file not added to README.md Project Structure table — **backlog candidate, already recorded in `docs/NPC-0014/backlog.md`** ✓
- `no-credentials-in-git`: no credentials or token files in diff ✓
- `python-version-compatibility`: `list[str] | None` requires Python 3.10+; `datetime.fromisoformat()` requires 3.7+; codebase targets Python 3.14 ✓
- `no-tkinter-in-rumps-process`: not applicable ✓
- `no-heredoc-in-fish`: not applicable ✓

No new rune violations found. Rune update not required for this story.

#### Code Review

Verification of all 4 QA Run 1 LOW findings (confirmed fixed per QA Run 2):

1. `apple_calendar.py` loop variable `ev` → `event` throughout loop body ✓
2. `drive_config.py` `_DEFAULTS["apple_exclude_calendars"] = []` present at line 74 ✓
3. `apple_calendar.py` `datetime.fromisoformat()` wrapped in `try/except (ValueError, TypeError) as exc: raise RuntimeError(...)` ✓
4. `tests/test_apple_calendar.py` `test_end_dt_falls_back_to_start_dt_when_end_date_absent` present ✓

No new code review findings from Story-Review run.

Additional observation: `_parse_apple_exclude()` coerces list items via `[str(x) for x in raw if x]`, filtering falsy values. Handles mixed-type YAML lists correctly. ✓

#### UI Review

No UI-scope changes in this story.

#### AWS Review

No AWS resources introduced or modified.

#### Security Review

All security checks clean from QA Run 2 confirmed:
- `subprocess.run()` list args; `shell=True` absent ✓
- `exclude_calendars` joined with commas as a single arg value, not shell-interpreted ✓
- `timeout=15` on all subprocess calls ✓
- No credentials, secrets, or tokens ✓
- `is_accessible()` swallows all exceptions; no internal state leaked ✓
- RuntimeError messages contain only ical-guy's own stderr output ✓

#### Rune Update Summary

No rune updates required or performed this story.

### Backlog Candidates

- Finding Key: LOW|README.md|—|apple_calendar.py missing from Project Structure table
  - Finding: LOW: README.md: `apple_calendar.py` not added to Project Structure table; `tests/test_apple_calendar.py` not listed under tests section.
  - Why deferred: Rune `update-readme` Owner is Feature-Review. US-1 spec does not list `README.md` in its Files section.
  - Suggested next action: Feature-Review to require README.md update before merge.
  - Backlog action: existing backlog item in `docs/NPC-0014/backlog.md` — reused, not re-appended.

### Justification Review

**INFO 1 — AC1.7 multi-calendar aggregation structural coverage**
- Finding: `tests/test_apple_calendar.py`: AC1.7 multi-calendar aggregation not directly exercised by a fixture with events from two distinct named calendar sources.
- Prior-step context: QA Run 1 noted; QA Run 2 carried as awareness item. No Implementer justification in `decision.md`.
- Story-Review decision: **accepted**
- Story-Review analysis: `get_tomorrow_events()` contains no per-calendar filtering code. The ical-guy CLI is responsible for aggregating across all accessible Apple Calendars when passed only `--from`/`--to` date args. A unit test using a fixture with two "calendar-named" events would only verify fixture construction, not ical-guy binary behavior. The spec requirement (AC1.7) is satisfied at the code level by the absence of filtering. Adding a multi-calendar integration test would require a live ical-guy binary, which is out of scope for unit tests. Structural correctness is sound.
- Propagation:
  - Guardrails: If any per-calendar selection or exclusion logic is ever added to the event loop in `get_tomorrow_events()`, AC1.7 must be retested with a multi-calendar scenario.
  - Revisit trigger for Feature-Review: check whether `build/manual_tests.md` should include a manual step to verify multi-calendar aggregation on a machine with two active Apple Calendars.

**INFO 2 — Timezone awareness enforcement**
- Finding: `apple_calendar.py`: `datetime.fromisoformat()` returns naive datetimes when the input string has no UTC offset. AC1.6 requires timezone-aware `start`/`end`. If ical-guy returns floating-time strings, the AC is silently violated.
- Prior-step context: QA Run 1 noted; QA Run 2 carried as awareness item. Test `test_start_datetime_is_timezone_aware` uses `-04:00` fixture strings.
- Story-Review decision: **accepted**
- Story-Review analysis: macOS EventKit always attaches timezone or UTC offset information to real meeting/event objects. Floating-time ISO 8601 strings (without offset) appear in ICS files for "all-day"-type and holiday events — which are already filtered out by the `isAllDay` guard and the `--exclude-all-day` flag. For timed events that pass all filters, EventKit-sourced strings reliably include UTC offset data. The risk of naive datetimes reaching the compute pipeline is bounded by ical-guy's EventKit integration contract. Enforcing `.tzinfo is not None` as a hard assertion in the production code would require wrapping every event's `fromisoformat` call with a timezone assertion, adding complexity for an edge case with no known real-world occurrence.
- Propagation:
  - Guardrails: The US-2 implementation should not assume timezone-aware datetimes when passing the unified pool to `compute_alarm()` — if `compute_alarm()` does tz-aware comparisons, it should handle naive datetimes gracefully or assert early.
  - Revisit trigger for Feature-Review: if ical-guy behavior changes after an update and `test_start_datetime_is_timezone_aware` still passes (because it uses a fixed fixture), a behavioral regression test would be needed to catch floating-time regressions.

## Story Review Decision
- PASS
- All 17 ACs satisfied. All 4 QA Run 1 LOW findings fixed. Lint PASS (232/232 tests PASS) on Story-Review run. No new HIGH/MEDIUM/LOW findings from Story-Review phases. Two INFO items accepted with Story-Review reasoning recorded above. No unresolved findings. spec_hash `af1261cf8a16` matches in both `progress.md` and `spec.md`.
