## QA Report — US-2: osaurus suggestion client module — 2026-05-17T00:00:00Z

### Missing Tests
- No AC-mandated test is absent. AC2.6 "exactly one stderr line" is tested for the API-call failure path; the yaml-load failure path (`test_yaml_failure_writes_stderr`) only asserts presence of the WARNING prefix — it does not assert the line count is exactly 1. The behavior is correct; the assertion is incomplete (INFO, see Issues).

### Negative Tests (minimum 3)
- `test_returns_none_for_unrecognised_response`: model returns string not in categories → None
- `test_connection_error_returns_none`: ConnectionError → None, no exception propagated
- `test_timeout_error_returns_none`: TimeoutError → None
- `test_generic_exception_returns_none`: arbitrary Exception → None
- `test_missing_yaml_returns_none`: FileNotFoundError on yaml load → None
- `test_unparseable_yaml_returns_none`: Exception on yaml.safe_load → None
- `test_returns_none_for_empty_response`: model returns empty string → None

### Edge Cases (minimum 3)
- `test_strips_whitespace_before_matching`: "  Interview  " matched correctly after strip
- `test_falls_back_to_foundation_when_default_module_absent`: `default_module: None` → model="foundation"
- `test_uses_model_from_config_when_overridden`: non-default `default_module` value honoured
- `test_openai_client_called_exactly_once_on_failure`: no retry path; call_count=1 even on exception

### Security Checklist
- [x] SQL/command injection? — No SQL or shell calls; no injection surface.
- [x] Auth bypass? — No auth logic; API key loaded from yaml and passed to openai SDK only.
- [x] Sensitive data in logs/responses? — Error handler logs `type(exc).__name__` only — no api_key, no title, no description, no response body. Verified by tests and code inspection.
- [x] Input validation at boundaries? — categories list validated by exact-match comparison; no exec/eval.
- [x] Confused deputy / privilege escalation? — Not applicable; no shared credentials or elevated paths.

### Performance Considerations
- Single HTTP call per invocation, `timeout=3.0` default — no retry, bounded latency.
- `_load_config()` reads from disk on every call — acceptable for a user-interactive popup flow; not called from unattended paths.

### Untested Assumptions
- `response.choices[0].message.content` is non-None when the openai SDK returns success. An empty `choices` list or a `None` content raises `IndexError`/`AttributeError`, which is caught by the `except Exception` handler. Behavior is correct; test coverage relies on the catch-all rather than an explicit assertion for this case.
- `osaurus.yaml` format always returns a dict from `yaml.safe_load`. A non-dict YAML file (e.g. a bare string) would cause `config.get(...)` to raise `AttributeError`, which is caught. Correct but not explicitly tested.

### How This Fails in Prod
- osaurus server not running → ConnectionError → `None` returned → caller must degrade gracefully (not enforced in this module).
- `osaurus.yaml` missing at deploy time → FileNotFoundError on every call → always `None`.
- Model returns a multi-word response with punctuation → no match → `None` silently; user sees no suggestion.
- Slow server (>3 s) → TimeoutError → `None` — default timeout is tight; caller may wish to make it configurable.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| Valid category returned | model="Interview" | "Interview" | YES |
| Whitespace stripped | model="  Interview  " | "Interview" | YES |
| Unrecognised response | model="Workshop" | None | YES |
| Empty response | model="" | None | YES |
| Connection error | ConnectionError | None | YES |
| Timeout error | TimeoutError | None | YES |
| Generic exception | Exception | None | YES |
| Missing osaurus.yaml | FileNotFoundError | None | YES |
| Unparseable osaurus.yaml | Exception (yaml) | None | YES |
| Model from config | default_module="foundation" | model="foundation" | YES |
| Model overridden | default_module="mymodel" | model="mymodel" | YES |
| Model fallback | default_module=None | model="foundation" | YES |
| temperature + max_tokens | any call | temp=0, max_tokens=32 | YES |
| Timeout forwarded | timeout=1.5 | OpenAI(timeout=1.5) | YES |
| No retry on success | success | create.call_count=1 | YES |
| No retry on failure | exception | create.call_count=1 | YES |
| Exactly one stderr line (API) | ConnectionError | len(lines)==1 | YES |
| api_key absent from stderr | ConnectionError | "test-key" not in stderr | YES |
| title/desc absent from stderr | Exception | title/desc not in stderr | YES |
| No live network calls | any | OpenAI always mocked | YES |
| Exactly one stderr line (yaml) | FileNotFoundError | len(lines)==1 | NO — only presence checked |

### Validation Runs
- Lint: FAIL — `ruff check osaurus_client.py tests/test_osaurus_client.py` → F401 unused `import sys` at `tests/test_osaurus_client.py:3`
- Unit tests: PASS — `python -m pytest tests/ -v` → 191/191

### Code Review

`osaurus_client.py`:
- No findings. Implementation is clean, exception handling is correct, no sensitive data leaks.

`tests/test_osaurus_client.py`:
- 🔴 bug: L3: `import sys` unused — ruff F401. Remove it; `patch("sys.stderr", ...)` targets by string and does not require `sys` in the test file's namespace.
- 🔵 nit: L284: `import osaurus_client  # noqa: E402` at bottom of file is unconventional. Functional but adds cognitive load. Not a blocking issue.
- 🔵 nit: `test_yaml_failure_writes_stderr` only asserts presence of `"[osaurus_client] WARNING:"` — does not assert exactly one line for the yaml-load failure path (compare with `test_failure_writes_exactly_one_stderr_line`). AC2.6 technically applies to all failure modes.

`requirements.txt`:
- No findings. `openai>=1.0,<3` added correctly between pyyaml and ruff.

`docs/runes/osaurus.md`:
- No findings. Rune updates are accurate, scoped, and consistent with implementation.

### UI Review
No UI-scope changes.

### AWS Review
No AWS-scope changes.

### Security Review
- No injection surfaces. No shell execution. No hardcoded credentials.
- `type(exc).__name__` pattern in both error handlers prevents accidental secret/title/description leakage in log output. ✓
- `osaurus.yaml` is gitignored (confirmed: `.gitignore` line 6). ✓
- `openai` SDK timeout bounded at constructor level — no unbounded blocking. ✓
- No findings.

### Backlog Candidates
- Finding Key: LOW|tests/test_osaurus_client.py|yaml_failure_path|missing exactly-one-line stderr assertion for yaml load failure
  - Finding: LOW: tests/test_osaurus_client.py: `test_yaml_failure_writes_stderr` checks WARNING presence only — does not assert exactly one line (AC2.6 applies to all failure paths)
  - Why deferred: Behavior is correct; this is a test assertion completeness issue within the current story's test file. Could be fixed in current story or deferred.
  - Suggested next action: Fix in current story (trivial — add `len([ln for ln in captured.getvalue().splitlines() if ln.strip()]) == 1` assertion) or carry to Story-Review
  - Backlog action: not appended (caller may fix inline per REWORK_REQUIRED)

### Justification Review
No LOW/INFO justifications in `decision.md` for US-2. Nothing to evaluate.

### Human Review Queue
(none)

### QA Loop Decision
- REWORK_REQUIRED
- Reason 1: Lint FAIL — `tests/test_osaurus_client.py:3` unused `import sys` (ruff F401). Phase 1 rule: lint failure → REWORK_REQUIRED.
- Reason 2: LOW finding (unused import) unresolved without justification in `decision.md`.
- Reason 3: LOW finding (README not updated per `update-readme` rune) unresolved without justification.

---

### Issues

#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
- L1: `tests/test_osaurus_client.py:L3` — `import sys` unused (ruff F401). Remove the import. Patch target `"sys.stderr"` is a string and does not require `sys` in scope.
- L2: `README.md` — not updated per `update-readme` rune. `openai>=1.0,<3` is a new runtime dependency; `osaurus_client.py` is a new source file at the project root. Both require README updates (dependency list and Project Structure table).

#### INFO
- I1: `tests/test_osaurus_client.py` — `test_yaml_failure_writes_stderr` checks warning presence but not "exactly one line". AC2.6 applies to all failure modes. Low risk (behavior is correct); consider tightening assertion.
- I2: `tests/smoke_imports.py` — `openai` package not added to smoke import list. No hard requirement to add it, but it would catch missing-install regressions before runtime.

---

### Spec Review

#### AC Coverage
- AC2.1: ✓ Covered — model, temperature, max_tokens, timeout all verified by `TestSuggestMeetingTypeParameters`.
- AC2.2: ✓ Covered — `test_returns_matched_category`, `test_strips_whitespace_before_matching`.
- AC2.3: ✓ Covered — `test_returns_none_for_unrecognised_response`, `test_returns_none_for_empty_response`.
- AC2.4: ✓ Covered — ConnectionError, TimeoutError, generic Exception all tested.
- AC2.5: ✓ Covered — `test_openai_client_called_exactly_once_on_success`, `test_openai_client_called_exactly_once_on_failure`.
- AC2.6: ✓ Covered (API failure path). INFO: yaml failure path not fully covered (see I1).
- AC2.7: ✓ Covered — missing yaml and unparseable yaml both tested.
- AC2.8: ✓ Covered — all tests patch `osaurus_client.OpenAI`; `TestNoLiveNetworkCalls` confirms mock presence.

#### Out-of-scope Changes
- None. Only touch-list files modified: `osaurus_client.py` (new), `tests/test_osaurus_client.py` (new), `requirements.txt` (openai added), `docs/runes/osaurus.md` (updated), `docs/NPC-0013/US-2/progress.md` (state file).

---

### Rune Review

#### osaurus-config-location
✓ All values loaded from `osaurus.yaml` (`server`, `api_key`, `default_module`). Nothing hardcoded. Schema in rune updated to include `default_module`.

#### osaurus-openai-client
✓ `OpenAI(base_url=f"{server}/v1", api_key=api_key, timeout=timeout)` — trailing slash stripped via `.rstrip("/")`. Rune updated to reflect `openai` as runtime dep in requirements.txt.

#### osaurus-model-selection
✓ Reads `default_module` from config with fallback `"foundation"`. Rune updated to use config key instead of hardcoded constant.

#### osaurus-prompt-design
✓ `temperature=0`, `max_tokens=32`, system prompt lists categories, instructs model to respond with only category name.

#### osaurus-not-in-production-pipeline
✓ `osaurus_client` not imported from `scheduler.py`, `app.py`, `main.py`, or `compute.py`. Confirmed by grep. Rune updated to name allowed call sites explicitly.

#### phantom-calendar / update-readme
⚠ LOW — README not updated. New runtime dep `openai>=1.0,<3` and new source file `osaurus_client.py` require README changes per `update-readme` rune.

#### phantom-calendar / update-build-tests-sh
✓ No structural change to `tests/` layout; `pytest tests/ -v` auto-discovers new file. No edit needed.

#### phantom-calendar / update-manual-tests-md
✓ No manual ACs in US-2. No edit needed.

#### phantom-calendar / no-credentials-in-git
✓ No credentials in diff. `osaurus.yaml` confirmed in `.gitignore`.

#### phantom-calendar / python-version-compatibility
✓ No deprecated Python 3.14 APIs used.
---

## QA Report — US-2: osaurus suggestion client module — 2026-05-17T08:00:00Z (Pass 2)

### Missing Tests
None. All AC-mandated test cases are covered. `test_yaml_failure_writes_stderr` now asserts exactly one stderr line (AC2.6 fully satisfied for all failure paths — I1 resolved).

### Negative Tests (minimum 3)
Unchanged from pass 1 — all 7 negative tests present and passing.

### Edge Cases (minimum 3)
Unchanged from pass 1 — all 4 edge-case tests present and passing.

### Security Checklist
- [x] SQL/command injection? — No change from pass 1. No injection surface.
- [x] Auth bypass? — No change.
- [x] Sensitive data in logs/responses? — `type(exc).__name__` pattern confirmed in both error handlers. ✓
- [x] Input validation at boundaries? — categories exact-match check unchanged. ✓
- [x] Confused deputy / privilege escalation? — Not applicable.

### Performance Considerations
No change from pass 1.

### Untested Assumptions
No change from pass 1.

### How This Fails in Prod
No change from pass 1.

### Test Matrix
| Scenario | Input | Expected | Covered? |
|----------|-------|----------|----------|
| All rows from pass 1 | — | — | (unchanged) |
| Exactly one stderr line (yaml) | FileNotFoundError | len(lines)==1 | YES — FIXED (was NO in pass 1) |

### Validation Runs
- Lint: PASS — `ruff check osaurus_client.py tests/test_osaurus_client.py tests/smoke_imports.py` → All checks passed!
- Unit tests: PASS — `python -m pytest tests/ -v` → 191/191

### Code Review

**Pass 1 findings resolved:**
- 🔴 bug (L1, pass 1): `import sys` at `tests/test_osaurus_client.py:L3` — FIXED. Import removed; lint now clean.
- 🔵 nit (pass 1): `test_yaml_failure_writes_stderr` only asserted WARNING presence — FIXED. Test now asserts `len(lines) == 1` and `assertIn("[osaurus_client] WARNING:", lines[0])`.

**Remaining nit (pass 1, unchanged):**
- 🔵 nit: `import osaurus_client  # noqa: E402` at bottom of test file. Lint-clean. No AC impact. Not escalated.

**New INFO:**
- INFO: `osaurus_client.py` uses `print(f"...", file=sys.stderr)` rather than `logging` per global python rune (`prefer logging over print`). This is spec-driven — AC2.6 explicitly requires "a single concise line to stderr", and `print(file=sys.stderr)` is the direct, test-compatible pattern (allows `patch("sys.stderr", ...)` in tests). Logging would require logger configuration and could risk multi-line or handler-routed output. Accepted.

### UI Review
No UI-scope changes.

### AWS Review
No AWS-scope changes.

### Security Review
No new findings. Previously verified clean in pass 1.

### Backlog Candidates
Finding Key `LOW|tests/test_osaurus_client.py|yaml_failure_path|missing exactly-one-line stderr assertion for yaml load failure` — RESOLVED. Test was updated in pass 2. Backlog entry not required.

### Justification Review
- Finding: INFO: `osaurus_client.py` uses `print(file=sys.stderr)` rather than `logging`
  - Implementer justification summary: No explicit decision.md entry for this finding. Implicit: spec AC2.6 requires "a single concise line to stderr"; `print(file=sys.stderr)` enables `patch("sys.stderr", ...)` in tests.
  - QA decision: accepted
  - QA analysis: The global python rune says "prefer logging over print". However, AC2.6 mandates a single stderr line and the tests verify this by patching `sys.stderr`. Using `logging` would require a configured handler pointing to stderr and could produce additional lines (e.g. tracebacks from propagation). The `print` pattern is idiomatic for tightly-scoped, test-verifiable stderr output. No production-logging intent here — the module is intentionally thin and stateless. Risk: if a future story adds richer error context, this pattern should be revisited to use `logging.warning(...)` with a NullHandler default.
  - Reviewer context: Acceptable for a single-function, spec-constrained module. Revisit if: (a) additional log levels are needed, (b) caller needs to suppress output programmatically, or (c) the module grows beyond one public function.

- Finding: INFO: decision.md entry 2026-05-17T07:00:00Z — README.md and smoke_imports.py additions
  - Implementer justification summary: rune `update-readme` requires README to reflect new runtime deps and source files; smoke_imports.py covers all runtime packages so adding openai is consistent. Both edits are additive and cannot regress other stories.
  - QA decision: accepted
  - QA analysis: README changes exactly match rune requirements (new source file, new runtime dep, optional osaurus note). smoke_imports.py addition catches missing-install regressions before runtime — consistent with existing pattern. Both verified in diff. No regression risk.
  - Reviewer context: Permanent acceptance. No revisit trigger needed.

### Human Review Queue
(none)

### QA Loop Decision
- PASS
- All HIGH/MEDIUM findings: none (pass 1 and pass 2).
- All LOW findings from pass 1 resolved: L1 (unused import) fixed, L2 (README) fixed.
- All INFO items from pass 1 resolved: I1 (yaml stderr exactly-one-line) fixed, I2 (smoke_imports openai) fixed.
- New INFO (print vs logging): accepted with bounded rationale.
- Remaining 🔵 nit (bottom import): lint-clean, no AC impact, no escalation.
- 191/191 tests pass. Lint clean. Spec hash verified.

### Issues

#### HIGH
(none)

#### MEDIUM
(none)

#### LOW
(none — all pass 1 LOWs resolved)

#### INFO
- I-pass2-1: `osaurus_client.py` uses `print(file=sys.stderr)` per AC2.6 spec constraint rather than `logging`. Accepted — see Justification Review.
- I-pass2-nit: `import osaurus_client  # noqa: E402` at bottom of test file. Lint-clean cosmetic issue. Not escalated.

### Spec Review

#### AC Coverage
No changes to ACs. All AC2.1–AC2.8 remain satisfied (see pass 1 for details). AC2.6 yaml-failure path now fully covered (I1 resolved).

#### Out-of-scope Changes
- README.md, tests/smoke_imports.py: additive-only changes, justified in decision.md, rune-required. Not out-of-scope.
- docs/runes/osaurus.md: rule corrections (openai runtime dep, not-in-production-pipeline). Rune-scope, no production code impact.

### Rune Review

#### osaurus-openai-client
✓ FIXED in rune: updated to state `openai` is a runtime dependency. Consistent with requirements.txt.

#### osaurus-not-in-production-pipeline
✓ FIXED in rune: explicit prohibition on importing `osaurus_client` from `scheduler.py`, `app.py`, `main.py`, `compute.py`. Named allowed call sites.

#### phantom-calendar / update-readme
✓ RESOLVED: README updated with osaurus_client.py in Project Structure, openai in Requirements, optional osaurus note. L2 from pass 1 closed.

All other rune rules: unchanged from pass 1 — all satisfied.
