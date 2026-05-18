## QA Report — US-1: apple_calendar.py — 2026-05-17

### Missing Tests
- `get_tomorrow_events()`: no test covers `endDate` absent/empty → `end_dt` fallback to `start_dt`
- `get_tomorrow_events()`: no test for malformed `startDate` string (non-ISO format) from ical-guy output

### Negative Tests (minimum 3)
- `test_returns_false_on_non_macos`: `is_accessible()` returns False on Linux, subprocess never called
- `test_raises_when_not_accessible`: `get_tomorrow_events()` raises RuntimeError when `is_accessible()` is False
- `test_raises_on_nonzero_exit`: `get_tomorrow_events()` raises RuntimeError when ical-guy exits non-zero
- `test_raises_on_unparseable_json`: `get_tomorrow_events()` raises RuntimeError on malformed stdout JSON
- `test_returns_false_when_probe_fails`: probe non-zero exit returns False from `is_accessible()`

### Edge Cases (minimum 3)
- `test_returns_false_when_mac_ver_empty`: empty `mac_ver` string handled without crash
- `test_returns_false_on_subprocess_timeout`: `TimeoutError` caught; returns False
- `test_untitled_event_gets_default_title`: `title=None` in event dict → `"Untitled"` in output
- `test_no_exclude_flag_when_none`: `exclude_calendars=None` → `--exclude-calendars` arg absent from subprocess call
- MISSING: `endDate` absent → `end_dt = start_dt` fallback (no test)

### Security Checklist
- [x] SQL/command injection? — `subprocess.run()` uses list form; no `shell=True`. `exclude_calendars` joined with commas passed as a single argument value, not interpreted by shell.
- [x] Auth bypass? — N/A. Module reads EventKit data via ical-guy CLI; no OAuth tokens or credentials involved.
- [x] Sensitive data in logs/responses? — No `logging` or `print` calls in `apple_calendar.py`. `RuntimeError` messages contain only ical-guy stderr, which is ical-guy's own output, no credentials.
- [x] Input validation at boundaries? — `target_date` is typed `date`; `exclude_calendars` is `list[str]|None`. `is_accessible()` guards before any subprocess for events. Acceptable.
- [x] Confused deputy / privilege escalation? — N/A. ical-guy runs under the invoking user's process; macOS Calendar permission is enforced by the OS.

### Performance Considerations
- All `subprocess.run()` calls carry `timeout=15`. ✓
- In-memory sort of events is O(n log n); acceptable for calendar event volumes.

### Untested Assumptions
- AC1.7 (multi-calendar aggregation): `get_tomorrow_events()` contains no per-calendar filtering; all ical-guy output events are included. The test uses a flat JSON array rather than events from two distinct named calendars. Structural correctness is sound, but this remains an untested assumption for ical-guy's behavior.
- Timezone awareness: AC1.6 requires `start`/`end` to be timezone-aware `datetime` objects. `datetime.fromisoformat()` returns naive datetimes when the input string has no UTC offset. The test fixture uses `-04:00` strings, so the timezone test passes. If ical-guy ever returns floating-time strings (no offset), `start.tzinfo` would be `None`, silently violating AC1.6.

### How This Fails in Prod
- ical-guy hangs indefinitely → `timeout=15` prevents. ✓
- macOS Calendar permission revoked mid-run → `is_accessible()` returns False on the next probe; `get_tomorrow_events()` raises `RuntimeError`; US-2 fallback to Google Calendar.
- ical-guy returns one event with a malformed `startDate` (non-ISO string) → `datetime.fromisoformat()` raises `ValueError` (not `RuntimeError`); the entire `get_tomorrow_events()` call aborts. The US-2 caller must catch both exception types.
- `exclude_calendars` list contains a name with a literal comma (e.g. `"Smith, John"`) → joined as `"Smith, John"` which ical-guy splits on commas, silently misinterpreting the calendar name. Limitation of the comma-delimited CLI arg design; no fix available without ical-guy API change.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|---|---|---|---|
| Non-macOS platform | `system=Linux` | `False` | ✓ |
| macOS version < 14 | `mac_ver=13.6.1` | `False` | ✓ |
| ical-guy not in PATH | `which=None` | `False` | ✓ |
| Probe exits non-zero | `returncode=1` | `False` | ✓ |
| Probe returns invalid JSON | `stdout="not json"` | `False` | ✓ |
| `mac_ver` empty string | `""` | `False` | ✓ |
| Subprocess timeout | `TimeoutError` | `False` | ✓ |
| All conditions met | macOS 15, ical-guy, valid JSON | `True` | ✓ |
| `is_accessible()` False → event read | — | `RuntimeError` | ✓ |
| Timed events for target date | 4 events (2 pass filters) | 2 events | ✓ |
| All-day events excluded | `isAllDay=True` | filtered out | ✓ |
| Events from other dates excluded | `startDate` on next day | filtered out | ✓ |
| `description` from `notes` | `notes="Daily sync"` | `"Daily sync"` | ✓ |
| `description` empty when notes null | `notes=None` | `""` | ✓ |
| `location` preserved / absent | `location="Room A"` / `None` | correct | ✓ |
| Sorted ascending by start | reversed event order | sorted | ✓ |
| ical-guy exits non-zero | `returncode=1` | `RuntimeError` | ✓ |
| Unparseable JSON output | `"not json at all"` | `RuntimeError` | ✓ |
| `exclude_calendars` arg passed | `["US Holidays","Birthdays"]` | `--exclude-calendars US Holidays,Birthdays` | ✓ |
| No exclude flag when `None` | `exclude_calendars=None` | no `--exclude-calendars` in args | ✓ |
| `title=None` default | `title=None` | `"Untitled"` | ✓ |
| Timezone-aware `start` | ISO string with `-04:00` | `tzinfo is not None` | ✓ |
| Empty event list | `[]` | `[]` | ✓ |
| Missing `endDate` fallback | `endDate=""` or absent | `end_dt = start_dt` | ✗ |
| Malformed `startDate` | `"not-a-date"` | skip or error? | ✗ |
| `apple_exclude_calendars` in config | YAML list | `list[str]` | ✓ |
| `apple_exclude_calendars` missing | no key | `[]` | ✓ |
| `apple_exclude_calendars` non-list | string value | `[]` | ✓ |
| `apple_exclude_calendars` empty list | `[]` | `[]` | ✓ |

### Validation Runs
- Lint: PASS — `ruff check apple_calendar.py drive_config.py tests/test_apple_calendar.py tests/test_drive_config.py` — no errors
- Unit tests: PASS — `python -m pytest tests/ -v` — 230/230 passed in 0.62s

### Code Review

`apple_calendar.py:L85`: `for ev in raw_events:` — `ev` is abbreviated. Python rune: prefer full words. Fix: rename to `event` throughout the loop body.

`drive_config.py`: `_DEFAULTS` dict does not include `"apple_exclude_calendars": []`. Spec implementation note says "Add `_DEFAULTS["apple_exclude_calendars"] = []` if a `_DEFAULTS` dict is used (consistent with existing keys)". `_DEFAULTS` is used for all other parse_config defaults. Omission is inconsistent; behavior is correct because `_parse_apple_exclude()` returns `[]` independently, but the module contract is broken. Fix: add `"apple_exclude_calendars": []` to `_DEFAULTS`.

`apple_calendar.py:L88-L89`: `start_dt = datetime.fromisoformat(start_str)` is unguarded. A malformed `startDate` string from ical-guy raises `ValueError`, aborting the entire function. This leaks a non-`RuntimeError` exception to the caller in US-2, which must catch both `ValueError` and `RuntimeError`. Fix: wrap in `try/except ValueError: continue` to skip malformed events, or document the exception contract explicitly (so the US-2 caller catches it).

### UI Review
No UI-scope changes.

### AWS Review
No AWS resources introduced or modified.

### Security Review
No vulnerabilities found.
- `subprocess.run()` uses list args (no `shell=True`); no command injection surface.
- `timeout=15` on all subprocess calls; no hang risk.
- No credentials, secrets, or tokens in the new module.
- `is_accessible()` swallows all exceptions and returns `False`; no internal state leaked to caller.
- `get_tomorrow_events()` raises `RuntimeError` on ical-guy errors; stderr content is included in the message but is ical-guy's own output, not sensitive application data.

### Backlog Candidates
- Finding Key: LOW|README.md|—|apple_calendar.py missing from Project Structure table
  - Finding: LOW: README.md: `apple_calendar.py` not added to Project Structure table; `tests/test_apple_calendar.py` not listed under tests
  - Why deferred: Rune `update-readme` Owner is Feature-Review; US-1 spec file list does not include `README.md`; deferring to Feature-Review enforcement gate
  - Suggested next action: Feature-Review to require README.md update before merge
  - Backlog action: appended

### Justification Review
No Implementer justifications present in `decision.md`. Only the initial state entry ("Decision: Initial state files created for US-1") is recorded. The LOW findings below are new and have no prior justification. Per protocol, all are unresolved.

### Human Review Queue
(none)

### QA Loop Decision
- REWORK_REQUIRED
- 4 unresolved LOW findings without Implementer justification in `decision.md`:
  1. `apple_calendar.py:L85` — abbreviated loop variable `ev` (Python naming rune)
  2. `drive_config.py` — `_DEFAULTS` missing `apple_exclude_calendars` key (spec implementation note)
  3. `apple_calendar.py:L88-L89` — unguarded `datetime.fromisoformat()` raises `ValueError` on malformed event, leaking non-`RuntimeError` to caller
  4. `tests/test_apple_calendar.py` — no test for `endDate` absent → `end_dt = start_dt` fallback path
- Each LOW must be fixed or justified in `decision.md` before QA can advance to PASS.

### Issues
#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
- `apple_calendar.py:L85`: Loop variable `ev` is abbreviated. Python rune requires full words. Rename to `event`.
- `drive_config.py`: `_DEFAULTS` dict does not include `"apple_exclude_calendars": []`. Spec implementation note requires it. Add the key.
- `apple_calendar.py:L88-L89`: `datetime.fromisoformat(start_str)` unguarded inside event loop. Malformed `startDate` raises `ValueError` (not `RuntimeError`), aborting the full function. Fix: wrap in `try/except ValueError: continue`, or update the US-2 caller contract to catch `ValueError` explicitly.
- `tests/test_apple_calendar.py`: Missing test for the `end_dt = start_dt` fallback when `endDate` is absent/empty string. Add a test event with no `endDate` and assert `end == start`.

#### INFO
- `tests/test_apple_calendar.py`: AC1.7 multi-calendar aggregation not directly exercised. Structural correctness is sound (no filtering code exists), but no test uses a fixture with events from two distinct named calendar sources.
- `apple_calendar.py`: No enforcement that `datetime.fromisoformat()` returns timezone-aware datetimes. AC1.6 requires timezone-aware `start`/`end`. If ical-guy returns floating-time strings, the AC is silently violated. ical-guy's macOS EventKit behavior makes this unlikely but it remains an untested assumption.

### Spec Review
#### AC Coverage
- AC1.1 ✓ — `test_returns_false_on_non_macos`
- AC1.2 ✓ — `test_returns_false_when_macos_version_too_old`
- AC1.3 ✓ — `test_returns_false_when_ical_guy_missing`
- AC1.4 ✓ — `test_returns_false_when_probe_fails`
- AC1.5 ✓ — `test_returns_true_on_success`
- AC1.6 ✓ (with caveat) — `test_start_datetime_is_timezone_aware` verifies timezone awareness for test fixture; assumption that ical-guy always returns aware strings (see INFO)
- AC1.7 ✓ (structural) — no calendar filtering in code; all ical-guy output included; multi-calendar scenario not directly exercised in tests
- AC1.8 ✓ — `test_exclude_calendars_passed_to_args`
- AC1.9 ✓ — `test_excludes_all_day_events`
- AC1.10 ✓ — `test_excludes_events_from_other_dates`
- AC1.11 ✓ — `test_sorted_by_start_ascending`
- AC1.12 ✓ — `test_raises_on_nonzero_exit` + `test_raises_on_unparseable_json`
- AC1.13 ✓ — `test_description_from_notes`
- AC1.14 ✓ — `test_description_empty_when_notes_null`
- AC1.15 ✓ — `test_parse_config_apple_exclude_calendars_present`
- AC1.16 ✓ — `test_parse_config_apple_exclude_calendars_missing`
- AC1.17 ✓ — `test_raises_when_not_accessible`

#### Out-of-scope Changes
None. All changes are confined to `apple_calendar.py` (new), `drive_config.py` (extended), `tests/test_apple_calendar.py` (new), `tests/test_drive_config.py` (extended) — exactly the files listed in the US-1 spec.

### Rune Review
- `update-readme` (LOW / Backlog): `apple_calendar.py` is a new source file in the project root. The rune requires updating README.md Project Structure table. Not done. Owner is Feature-Review; deferred as backlog candidate (see above).
- `update-build-tests-sh`: `python -m pytest tests/ -v` auto-discovers new test files; `build/tests.sh` requires no changes. ✓
- `update-manual-tests-md`: US-1 has no manual-only ACs; all criteria are automatable. No `manual_tests.md` entry required. ✓
- `python-version-compatibility`: `datetime.fromisoformat()` is available since Python 3.7; `list[str] | None` union type hint requires Python 3.10+. Codebase targets Python 3.14 (venv: `uv venv --python 3.14`). ✓
- `no-credentials-in-git`: `apple_calendar.py` introduces no credentials. ✓
- `no-heredoc-in-fish`: Not applicable (no shell scripts added). ✓
- `no-tkinter-in-rumps-process`: Not applicable (no UI in this module). ✓
---

## QA Report — US-1: apple_calendar.py — 2026-05-17 (Run 2)

### Missing Tests
None. Both tests flagged in Run 1 are now present:
- `test_end_dt_falls_back_to_start_dt_when_end_date_absent` — `endDate=""` → `end_dt == start_dt` ✓
- `test_raises_runtime_error_on_malformed_start_date` — `startDate="not-a-date"` → `RuntimeError` with "invalid startDate" ✓

### Negative Tests (minimum 3)
Unchanged from Run 1 — all 5 negative tests confirmed present. ✓

### Edge Cases (minimum 3)
All edge cases from Run 1 confirmed; two new cases now covered:
- `test_end_dt_falls_back_to_start_dt_when_end_date_absent`: absent `endDate` → `end == start` ✓
- `test_raises_runtime_error_on_malformed_start_date`: malformed `startDate` → `RuntimeError("...invalid startDate...")` ✓

### Security Checklist
- [x] SQL/command injection? — `subprocess.run()` list form; no `shell=True`. ✓
- [x] Auth bypass? — N/A. ✓
- [x] Sensitive data in logs/responses? — No print/logging in module; RuntimeError messages contain only ical-guy stderr. ✓
- [x] Input validation at boundaries? — `target_date: date`, `exclude_calendars: list[str]|None`; `is_accessible()` guards first. ✓
- [x] Confused deputy / privilege escalation? — N/A. macOS Calendar permission enforced by OS. ✓

### Performance Considerations
Unchanged. All `subprocess.run()` calls carry `timeout=15`. Sort is O(n log n). ✓

### Untested Assumptions
Unchanged from Run 1:
- AC1.7 multi-calendar aggregation: structural correctness is sound (no filtering code); multi-calendar fixture not exercised.
- Timezone awareness: ical-guy floating-time strings would yield naive datetimes. Considered INFO — ical-guy macOS EventKit behavior makes this unlikely.

### How This Fails in Prod
Unchanged from Run 1, with one update: malformed `startDate` now raises `RuntimeError` (not bare `ValueError`), so US-2's `except Exception` handler catches it cleanly and falls back to Google Calendar.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| Non-macOS platform | `system=Linux` | `False` | ✓ |
| macOS version < 14 | `mac_ver=13.6.1` | `False` | ✓ |
| ical-guy not in PATH | `which=None` | `False` | ✓ |
| Probe exits non-zero | `returncode=1` | `False` | ✓ |
| Probe returns invalid JSON | `stdout="not json"` | `False` | ✓ |
| `mac_ver` empty string | `""` | `False` | ✓ |
| Subprocess timeout | `TimeoutError` | `False` | ✓ |
| All conditions met | macOS 15, ical-guy, valid JSON | `True` | ✓ |
| `is_accessible()` False → event read | — | `RuntimeError` | ✓ |
| Timed events for target date | 4 events (2 pass filters) | 2 events | ✓ |
| All-day events excluded | `isAllDay=True` | filtered out | ✓ |
| Events from other dates excluded | `startDate` on next day | filtered out | ✓ |
| `description` from `notes` | `notes="Daily sync"` | `"Daily sync"` | ✓ |
| `description` empty when notes null | `notes=None` | `""` | ✓ |
| `location` preserved / absent | `location="Room A"` / `None` | correct | ✓ |
| Sorted ascending by start | reversed event order | sorted | ✓ |
| ical-guy exits non-zero | `returncode=1` | `RuntimeError` | ✓ |
| Unparseable JSON output | `"not json at all"` | `RuntimeError` | ✓ |
| `exclude_calendars` arg passed | `["US Holidays","Birthdays"]` | `--exclude-calendars US Holidays,Birthdays` | ✓ |
| No exclude flag when `None` | `exclude_calendars=None` | no `--exclude-calendars` | ✓ |
| `title=None` default | `title=None` | `"Untitled"` | ✓ |
| Timezone-aware `start` | ISO string with `-04:00` | `tzinfo is not None` | ✓ |
| Empty event list | `[]` | `[]` | ✓ |
| Missing `endDate` fallback | `endDate=""` | `end == start` | ✓ (new) |
| Malformed `startDate` | `"not-a-date"` | `RuntimeError("...invalid startDate...")` | ✓ (new) |
| `apple_exclude_calendars` in config | YAML list | `list[str]` | ✓ |
| `apple_exclude_calendars` missing | no key | `[]` | ✓ |
| `apple_exclude_calendars` non-list | string value | `[]` | ✓ |
| `apple_exclude_calendars` empty list | `[]` | `[]` | ✓ |

### Validation Runs
- Lint: PASS — `ruff check apple_calendar.py drive_config.py tests/test_apple_calendar.py tests/test_drive_config.py` — no errors
- Unit tests: PASS — `python -m pytest tests/` — 232/232 passed (+2 vs Run 1)

### Code Review

Verification of all 4 Run 1 LOW findings:

1. `apple_calendar.py` loop variable — `for ev in raw_events:` → `for event in raw_events:` throughout loop body. **FIXED.** ✓
2. `drive_config.py` `_DEFAULTS` — `"apple_exclude_calendars": []` present in `_DEFAULTS` dict at line 76. **FIXED.** ✓
3. `apple_calendar.py` `startDate` parsing — now `try: start_dt = datetime.fromisoformat(start_str) except (ValueError, TypeError) as exc: raise RuntimeError(f"ical-guy returned invalid startDate {start_str!r}: {exc}") from exc`. Raises `RuntimeError` (not bare `ValueError`); caller's `except Exception` covers it. **FIXED.** ✓
4. `tests/test_apple_calendar.py` missing endDate fallback test — `test_end_dt_falls_back_to_start_dt_when_end_date_absent` added. **FIXED.** ✓

No new code review findings.

Note on Fix 3 design: Implementer chose to raise `RuntimeError` on malformed `startDate` rather than skipping the event and continuing. This is a valid interpretation of the QA Run 1 finding (which offered both options). Raising is preferable — a batch with a corrupt event signals a data integrity issue best surfaced to the caller. US-2 catches all exceptions and falls back to Google Calendar. ✓

Note on `endDate` error handling: `except (ValueError, TypeError): end_dt = start_dt` — silently falls back. Correct: missing/malformed `endDate` has a sensible default (same as start); a missing `startDate` does not. Asymmetry is intentional and sound.

### UI Review
No UI-scope changes.

### AWS Review
No AWS-scope changes.

### Security Review
No vulnerabilities. All findings from Run 1 Security Review remain clean:
- `subprocess.run()` list args; no `shell=True`.
- `timeout=15` on all subprocess calls.
- No credentials, secrets, or tokens.
- `is_accessible()` swallows all exceptions; no internal state leaked.
- New RuntimeError for malformed `startDate` includes only the raw value from ical-guy output — no sensitive data.

### Backlog Candidates
- Finding Key: LOW|README.md|—|apple_calendar.py missing from Project Structure table
  - Backlog action: existing backlog item from Run 1 — reused, not re-appended

### Justification Review
No justification review required. All 4 LOW findings from Run 1 were resolved by code fixes, not by Implementer justification. `decision.md` contains only the initial state entry, which is correct. No outstanding unresolved findings to evaluate.

### Human Review Queue
(none)

### QA Loop Decision
- PASS
- All 4 LOW findings from Run 1 are fixed. Lint PASS. 232/232 tests PASS (+2 new tests). No new HIGH/MEDIUM/LOW findings. Two INFO items from Run 1 remain acknowledged and require no action. Backlog candidate (README.md) deferred to Feature-Review as before.

### Issues
#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
(none — all Run 1 LOW findings resolved)

#### INFO
- `tests/test_apple_calendar.py`: AC1.7 multi-calendar aggregation not directly exercised. No calendar filtering code exists, so correctness is structurally sound. Carry to Story-Review as awareness item.
- `apple_calendar.py`: No enforcement that `datetime.fromisoformat()` returns timezone-aware datetimes. ical-guy macOS EventKit behavior makes floating-time strings unlikely. Carry to Story-Review as awareness item.

### Spec Review
#### AC Coverage
AC1.1–AC1.17: all covered. No change from Run 1. ✓

#### Out-of-scope Changes
None. Changes confined to `apple_calendar.py`, `drive_config.py`, `tests/test_apple_calendar.py`, `tests/test_drive_config.py`.

### Rune Review
- `update-readme` (LOW / Backlog): unchanged — still deferred to Feature-Review.
- All other rune rules: unchanged from Run 1. All pass. ✓
