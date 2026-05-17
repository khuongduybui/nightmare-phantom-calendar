## Story Review Report — US-3: Wire suggestion + recurring/one-shot dialogs into the sync popup — 2026-05-17T14:00:00Z

### Validation Runs
- Lint: **PASS** — `ruff check sync_job.py tests/test_classification_ui.py tests/test_classification_write.py tests/test_sync_job.py` → "All checks passed!"
- Unit tests: **PASS** — `python -m pytest tests/ -q` → 202/202 passed in 0.64s

---

## Story Review Findings

### Phase 1 — Preliminary Review

**State files**
- `progress.md`: phase = QA, status = Done ✓
- `spec_hash` in progress.md = `ba1561a5443c`; spec_hash in spec.md front matter = `ba1561a5443c` ✓
- `decision.md`: rationale present for both non-obvious changes (personal_events routing via `result["personal_events"]`; `timedelta` moved to module level) ✓
- `qa_report.md`: present; QA pass 2 decision = PASS ✓

No Phase 1 findings.

---

### Phase 2 — Spec Review

**Acceptance Criteria coverage**

| AC | Status | Notes |
|---|---|---|
| AC3.1 | ✓ | `default_item = suggestion` path verified; `test_suggestion_used_as_default_item` asserts `default items {"Interview"}` |
| AC3.2 | ✓ | None → `"Skip (keep default)"` default; `test_no_suggestion_falls_back_to_skip` asserts `default items {"Skip (keep default)"}` |
| AC3.3 | ✓ | Second Recurring/One-shot dialog shown after non-Skip selection; `test_recurring_oneshot_dialog_shown_after_type_selection` |
| AC3.4 | ✓ | Recurring → entry appended with `start_time`, `meeting_type`, `prep_minutes`; `test_non_skipped_classification_recurring_in_response` |
| AC3.5 | ✓ | One-shot → not appended, alarm still updated; `test_non_skipped_classification_oneshot_not_in_response` |
| AC3.6 | ✓ | `_classify_personal_events` exists, called from `_show_popup` after `_prompt_unknown_locations` for non-baseline non-empty results; `TestClassifyPersonalEvents` suite (5 tests) |
| AC3.7 | ✓ | `is_baseline=True` skips both `_classify_unknown_blocks` and `_classify_personal_events`; `first_meeting_name=None` early-returns before either is reached |
| AC3.8 | ✓ | Exception in `suggest_meeting_type` caught by inner try/except; dialog still opens with Skip default; `test_exception_in_suggest_falls_back_gracefully` |
| AC3.9 | ✓ | All 8 required test cases present: pre-selected suggestion, absent suggestion, accepts→Recurring, accepts→One-shot, **user overrides** (`test_user_overrides_suggestion`, added pass 2), Skip, personal-event happy path, exception fallback |
| AC3.10 | ✓ | 202/202 tests pass; `test_classification_write.py` and `test_sync_job.py` unaffected |
| AC3.11 | ✓ | `run_calendar_write` and `append_recurring_meetings` call sites in `run_nightly_sync` unchanged; receive only Recurring-classified entries |

**Scope check**
Changed files (`sync_job.py`, `tests/test_classification_ui.py`, state files) are all within the spec's declared file touch list. `test_classification_write.py` and `test_sync_job.py` required no modifications per spec. No out-of-scope changes detected.

**QA rules**
- QA remained review-only ✓
- No tests deleted or relaxed ✓
- All HIGH findings: none ✓
- All MEDIUM findings resolved (M1 — user-override test added in pass 2) ✓
- All LOW findings resolved (L1/L2/L3 lint clean in pass 2; L4 `timedelta` at module level) ✓
- INFO findings I1/I2/I3 accepted by QA with documented justification; reviewed below ✓

---

### Phase 3 — Review Core

#### Rune Review

Component runes evaluated: `phantom-calendar.md`, `osaurus.md`

| Rule | Status | Notes |
|---|---|---|
| `no-tkinter-in-rumps-process` | ✓ PASS | All dialogs use `subprocess.run(["osascript", ...])` via `_osascript()`. No tkinter in diff. |
| `no-credentials-in-git` | ✓ PASS | `credentials.json`, `token.json`, `osaurus.yaml` absent from diff. `osaurus.yaml` remains gitignored. |
| `python-version-compatibility` | ✓ PASS | No deprecated APIs. `datetime` usage at module level; no `datetime.utcnow()`. |
| `venv-and-uv-conventions` | ✓ PASS | No bare `python` or `pip` in diff. |
| `osaurus-config-location` | ✓ PASS | No hardcoded server URL or API key. `osaurus_client.py` loads all values from `osaurus.yaml` (per US-2). |
| `osaurus-openai-client` | ✓ PASS | `openai` in `requirements.txt` as runtime dependency (per US-2). |
| `osaurus-model-selection` | ✓ PASS | Model read from `osaurus.yaml` `default_module` with `"foundation"` fallback (per US-2 `osaurus_client.py`). |
| `osaurus-prompt-design` | ✓ PASS | `temperature=0`, `max_tokens=32`, system prompt enforces single-value response (per US-2 implementation). |
| `osaurus-not-in-production-pipeline` | ✓ PASS | `osaurus_client` imported only in `sync_job.py`. Calls inside `_classify_unknown_blocks` and `_classify_personal_events` — both popup-driven, user-interactive, non-scheduler paths. Verified absent from `scheduler.py`, `app.py`, `main.py`, `compute.py`. Rune already names both helpers in its allowed-paths list. |
| `local-state-files-in-gitignore` | ✓ PASS | No new local state files introduced. |
| `update-readme` | DEFERRED | Feature-Review owner. |
| `update-manual-tests-md` | DEFERRED | Feature-Review owner. Manual test entries (osaurus suggestion accepted Recurring, suggestion overridden, osaurus stopped fallback) to be added at Feature-Review. |

Global rune (`python.instructions.md`): `prefer logging over print` — see INFO I3 justification below.

No rune violations. No rune updates required for this story; `osaurus-not-in-production-pipeline` already names `_classify_personal_events`. The `update-readme` / `update-manual-tests-md` rune update (for production dependency promotion) is Feature-Review scope per the spec.

**Rune Update Summary:** None. All rune rules satisfied or deferred to Feature-Review owner.

---

#### Code Review

**`sync_job.py` — new `_ask_recurring_or_oneshot()` helper**
- Returns `rc == 0 and out.strip() == "Recurring"` — correctly treats cancel (rc≠0) as One-shot per spec. ✓
- Button layout: `{"One-shot", "Recurring"} default button "Recurring"` — default Recurring as spec requires. ✓
- Delegates to `_osascript()` — consistent with codebase dialog pattern. ✓

**`sync_job.py` — modified `_classify_unknown_blocks()`**
- `timedelta` moved to module-level import (`from datetime import datetime, timedelta` at line 6) — LOW L4 from QA pass 1 resolved. ✓
- Belt-and-suspenders `try/except Exception` around `osaurus_client.suggest_meeting_type` — `suggestion = None` on any exception. Client already catches internally; this ensures no sync kill on client refactor. ✓
- `default_item = suggestion if suggestion else "Skip (keep default)"` — correct AC3.1/AC3.2 implementation. ✓
- `_ask_recurring_or_oneshot()` called only after non-Skip selection; Recurring appends to classifications, One-shot skips append. ✓
- Category filter `isinstance(prep, int)` — travel-time entries (`"travel+N"` strings) excluded. ✓
- Pre-existing inline `from compute import resolve_prep_minutes` inside function body — outside US-3 touch scope; see I1 below.

**`sync_job.py` — new `_classify_personal_events()`**
- Mirrors MSI block flow: same osaurus call, same dialog, same Recurring/One-shot branch. ✓
- `if start is None: continue` — defensive guard per decision.md. ✓
- Does NOT call `_ask_location` — correct: personal event location prompting is handled upstream by `_prompt_unknown_locations`, not here. ✓
- Uses `prep_minutes` directly (no `resolve_prep_minutes` call) — consistent with spec which says "append entry using the existing entry shape (start_time, meeting_type, prep_minutes)" and separates location/travel adjustment into `_prompt_unknown_locations`. ✓
- `safe_title = title.replace('"', "'")` — consistent with codebase quoting pattern for osascript string embedding. ✓

**`sync_job.py` — modified `_show_popup()`**
- Order: `_classify_unknown_blocks` → `_prompt_unknown_locations` → `_classify_personal_events` → main popup — matches spec-declared order. ✓
- `classifications.extend(personal_classifications)` — merges personal event classifications into unified list for `run_calendar_write`. ✓
- All three helpers gated on `not result.get("is_baseline")` and `config` presence. ✓

**`sync_job.py` — modified `run_nightly_sync()`**
- `result["personal_events"] = [e for e in personal_events if "Alarm" not in e.get("title", "")]` — attaches filtered personal events before `_show_popup`; filter excludes alarm events (pre-existing codebase pattern). ✓
- `run_calendar_write` and `append_recurring_meetings` call sites verified unchanged — AC3.11 satisfied. ✓

**`tests/test_classification_ui.py`**
- `MagicMock` and `call` unused imports removed — lint clean. ✓
- `response` variable now asserted in `test_non_skipped_classification_oneshot_not_in_response` — `self.assertEqual(response["classifications"], [])`. ✓
- `test_user_overrides_suggestion` added: suggestion="Interview", user picks "Daily standup" → `response["classifications"][0]["meeting_type"] == "Daily standup"`. AC3.9 override path covered. ✓
- Side-effect ordering in new test matches actual call sequence (classify → location → recurring → main popup). ✓
- `TestClassifyPersonalEvents`: 5 tests covering Recurring, One-shot, Skip, baseline skip, no-meetings skip. ✓
- `import sync_job` at bottom of file (after class definitions) — established pattern. ✓

No code review findings that weren't already resolved in QA pass 2.

---

#### UI Review

No UI-scope changes. All dialogs are osascript-based; no visual layout, component, or style changes.

---

#### AWS Review

No AWS-scope changes.

---

#### Security Review

- **Injection** — `subprocess.run(["osascript", "-e", script], ...)` list form prevents shell injection. User-controlled strings (`title`, `location`) embedded in osascript via `safe_title.replace('"', "'")` — consistent with established codebase quoting pattern. `osaurus_client` failure path logs only exception class name: no API key, title, description, or response body in any stderr output. ✓
- **Auth/authz** — No auth boundaries in scope. ✓
- **Secrets** — No hardcoded credentials, API keys, or tokens. `osaurus.yaml` gitignored; absent from diff. ✓
- **Input validation** — `suggest_meeting_type` response validated against `categories` list before use as `default items` (per US-2 implementation). ✓
- **Confused deputy** — None in scope. ✓

No security findings.

---

### Justification Review

#### Finding: INFO I1 — Pre-existing inline imports outside US-3 scope
- Finding: INFO: `sync_job.py:_prompt_unknown_locations`: `from datetime import timedelta` and `from datetime import datetime as _dt` inline imports are pre-existing code unchanged in US-3. `sync_job.py:_classify_unknown_blocks`: `from compute import resolve_prep_minutes` inline import is also pre-existing.
- Prior-step context: Implementer decision.md entry documents that US-3 moved the `timedelta` used by `_classify_unknown_blocks` to module level (L4 fix) but left the pre-existing inline imports in `_prompt_unknown_locations` and `_classify_unknown_blocks` untouched as they are outside the US-3 touch scope. QA accepted: out-of-scope, no correctness impact, risk low.
- Story-Review decision: **accepted**
- Story-Review analysis: QA's reasoning is sound. The module-level `from datetime import datetime, timedelta` at line 6 already provides both names. The remaining inline imports are vestigial dead weight from pre-US-3 code. Moving them now would: (a) violate implementation discipline (touching out-of-scope lines), (b) risk a merge conflict if concurrent work touches the same function, (c) introduce no correctness benefit. The code compiles and lints cleanly; the inline imports shadow the module-level ones without ill effect.
- Propagation (accepted): If `_prompt_unknown_locations` or `_classify_unknown_blocks` is modified in a future story, the reviewer should require these inline imports be moved to module level at that time. The module-level import already exists; the fix is a one-line deletion in each function. Revisit trigger: any story that modifies `_prompt_unknown_locations` or `_classify_unknown_blocks`.

#### Finding: INFO I2 — `test_no_meetings_skips_personal_classification` uses `personal_events: []`
- Finding: INFO: `tests/test_classification_ui.py:~315`: early-return path for `first_meeting_name=None` with non-empty `personal_events` not explicitly tested.
- Prior-step context: QA accepted with structural analysis: the early return (`if meeting_name is None: return {...}`) occurs before `personal_events` is accessed, so the test value is irrelevant to the assertion.
- Story-Review decision: **accepted**
- Story-Review analysis: Confirmed by code inspection — `_show_popup` checks `meeting_name = result.get("first_meeting_name")` as its first substantive operation and returns immediately if `None`. The `personal_events` key is not accessed until after the `classifications: list = []` initialization block, which is never reached on the no-meetings path. The test's `personal_events: []` does not weaken the assertion; a non-empty list would produce identical behavior. Risk: negligible.
- Propagation (accepted): If `_show_popup` is refactored to access `personal_events` earlier (e.g., to display a count in the no-meetings dialog), update this test to use a non-empty list to validate the early-return still fires. Revisit trigger: any refactor of the no-meetings path in `_show_popup`.

#### Finding: INFO I3 — `print(file=sys.stderr)` vs `logging`
- Finding: INFO: `sync_job.py`: `print` used throughout — global rune (`python.instructions.md`) prefers `logging`.
- Prior-step context: Established codebase pattern across NPC-0004 through NPC-0013. QA accepted as cross-cutting concern requiring a dedicated refactor story.
- Story-Review decision: **accepted**
- Story-Review analysis: US-3 introduces no new `print` calls beyond what is already present in the file. The new functions (`_ask_recurring_or_oneshot`, `_classify_personal_events`) do not add any `print` statements. The issue is a pre-existing codebase-wide convention gap, not a US-3 regression. Correcting it here would be an out-of-scope change touching dozens of lines across multiple functions. Risk for correctness: zero. Risk for observability: minor, and bounded by the fact that all stderr output is visible in terminal/system logs.
- Propagation (accepted): Address in a dedicated `print → logging` migration story that covers all of `sync_job.py` at once. Revisit trigger: when that migration story is planned. Feature-Review should note this in the backlog.

---

### Backlog Candidates

No new backlog candidates from Story-Review. The pass 1 QA backlog candidate (INFO|tests/test_classification_ui.py|315|test_no_meetings_skips_personal_classification uses empty personal_events) remains INFO-level and accepted; no escalation required. Not appended to backlog.md.

---

## Story Review Decision
- **PASS**
- Lint PASS (ruff clean). Tests PASS (202/202). Spec hash matches (`ba1561a5443c`). All AC3.1–AC3.11 covered. No HIGH/MEDIUM findings. All LOW findings resolved by Implementer between QA passes. Three INFO findings evaluated and accepted with Story-Review reasoning documented above. No prior Story-Review run exists; repeat-escalation rule does not apply.
