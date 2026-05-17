## Story Review Report — US-2: osaurus suggestion client module — 2026-05-17T09:00:00Z

### Validation Runs
- Lint: PASS — `ruff check osaurus_client.py tests/test_osaurus_client.py tests/smoke_imports.py` → All checks passed!
- Unit tests: PASS — `python -m pytest tests/ -q` → 191 passed in 0.62s

---

## Story Review Findings

### Phase 1 — Preliminary Review

**State files**
- ✅ `progress.md` status is `Done`, phase is `QA`
- ✅ `decision.md` has rationale for both deviations: initial state creation (2026-05-17T00:00:00Z) and the out-of-touch-list edits to README.md and smoke_imports.py (2026-05-17T07:00:00Z), with rune justification cited.
- ✅ `spec_hash: 'ba1561a5443c'` in `progress.md` matches `spec_hash: 'ba1561a5443c'` in `spec.md` front matter.

No preliminary findings.

---

### Phase 2 — Spec Review

**Acceptance Criteria**

- AC2.1 ✅ — `suggest_meeting_type(...)` issues exactly one `chat.completions.create()` call with `model` read from `config.get("default_module") or "foundation"`, `temperature=0`, `max_tokens=32`, and `timeout` forwarded to the `OpenAI` constructor. Tests: `TestSuggestMeetingTypeParameters` (5 tests: model from config, override, fallback, temperature+max_tokens, timeout). Implementation: `osaurus_client.py` lines 56–67.
- AC2.2 ✅ — Returns matched category when `response.choices[0].message.content.strip()` is in `categories`. Tests: `test_returns_matched_category`, `test_strips_whitespace_before_matching`.
- AC2.3 ✅ — Returns `None` when stripped response is not in `categories`. Tests: `test_returns_none_for_unrecognised_response`, `test_returns_none_for_empty_response`.
- AC2.4 ✅ — Returns `None` on `ConnectionError`, `TimeoutError`, and generic `Exception` from the openai call. Tests: three distinct exception tests in `TestSuggestMeetingTypeExceptions`.
- AC2.5 ✅ — No retry: exactly one `chat.completions.create` call on both success and failure paths. Tests: `test_openai_client_called_exactly_once_on_success`, `test_openai_client_called_exactly_once_on_failure`.
- AC2.6 ✅ — On failure, exactly one non-empty stderr line containing `[osaurus_client] WARNING: <ClassName>` only — no api_key, title, description, or response body. Tests: `test_failure_writes_exactly_one_stderr_line`, `test_stderr_does_not_contain_api_key`, `test_stderr_does_not_contain_title_or_description`, `test_yaml_failure_writes_stderr` (now asserts exactly one line, fixed in QA pass 2).
- AC2.7 ✅ — `_load_config()` failure (FileNotFoundError, yaml parse error) caught at the outer `try` block, logs one stderr line, returns `None`. Tests: `test_missing_yaml_returns_none`, `test_unparseable_yaml_returns_none`, `test_yaml_failure_writes_stderr`.
- AC2.8 ✅ — All tests patch `osaurus_client._load_config` and `osaurus_client.OpenAI`. `TestNoLiveNetworkCalls` confirms mock presence. No live HTTP traffic.

**Scope check**
- ✅ All touched files are on the touch list (osaurus_client.py, requirements.txt, tests/test_osaurus_client.py, docs/runes/osaurus.md) or justified out-of-list in decision.md (README.md, tests/smoke_imports.py, state files).
- ✅ No changes to scheduler.py, app.py, main.py, compute.py, sync_job.py, or any other production files. Grep confirms osaurus_client is not imported from any prohibited path.

**QA rules**
- ✅ QA remained review-only — no production/test edits by QA.
- ✅ No tests deleted or relaxed.
- ✅ No HIGH findings in either QA pass.
- ✅ No MEDIUM findings.
- ✅ All LOWs from QA pass 1 resolved (L1: unused import removed; L2: README updated). No LOWs in pass 2.
- ✅ INFO items from pass 1 resolved (I1: yaml stderr exactly-one-line assertion tightened; I2: smoke_imports.py openai added). One INFO in pass 2 (print vs logging) accepted by QA with documented rationale.

No Phase 2 findings.

---

### Phase 3 — Review Core

#### Rune Review

Global rune (`python.instructions.md`):
- Rule: "prefer `logging` over `print`" — `osaurus_client.py` uses `print(f"...", file=sys.stderr)` in both error handlers. Carried as INFO (see Justification Review).

Component rune — `osaurus.md`:
- `osaurus-config-location` ✅ — server, api_key, default_module all loaded from osaurus.yaml via `_load_config()`. Nothing hardcoded.
- `osaurus-openai-client` ✅ — `OpenAI(base_url=f"{server}/v1", api_key=api_key, timeout=timeout)` with `.rstrip("/")` on server URL. `openai>=1.0,<3` in requirements.txt as runtime dep.
- `osaurus-model-selection` ✅ — `config.get("default_module") or _DEFAULT_MODEL_FALLBACK` with fallback `"foundation"`.
- `osaurus-prompt-design` ✅ — `temperature=0`, `max_tokens=32`, system prompt explicitly lists categories and instructs model to respond with only the category name, no explanation.
- `osaurus-not-in-production-pipeline` ✅ — osaurus_client.py not imported from scheduler.py, app.py, main.py, or compute.py. Confirmed by grep.

Component rune — `phantom-calendar.md`:
- `update-readme` ✅ — README updated: osaurus_client.py in Project Structure (L129), optional osaurus note in Requirements (L12), openai-compatible reference in osaurus_client.py entry. Consistent with rune requirement.
- `update-build-tests-sh` ✅ — `pytest tests/ -v` auto-discovers new test file. No structural change to `tests/`. No edit needed.
- `update-manual-tests-md` ✅ — No manual ACs in US-2.
- `no-credentials-in-git` ✅ — osaurus.yaml confirmed gitignored. No credentials in any diff file.
- `python-version-compatibility` ✅ — No deprecated 3.14 APIs. `os.path`, `yaml.safe_load`, `open()`, openai SDK usage all current.
- `local-state-files-in-gitignore` ✅ — No new runtime state files introduced.

Rune update summary: `osaurus.md` was updated by Implementer in pass 1 — openai promoted to runtime dep, not-in-production-pipeline rule names allowed call sites explicitly. Both updates are accurate, scoped, and consistent with the implementation. No further rune updates required.

#### Code Review

`osaurus_client.py` — Clean implementation. No findings.
- Exception handling is correct: two independent try/except blocks — one for yaml load, one for the network call. Catch-all `except Exception` is appropriate for a degrading-gracefully module.
- `_DEFAULT_MODEL_FALLBACK` constant cleanly expresses the fallback intent.
- `_load_config()` helper correctly enables independent testability of the yaml-failure path (AC2.7).
- `str | None` return type annotation as a forward-reference string is correct for Python 3.9 compatibility (osaurus.yaml may be loaded in any Python version ≥3.9). No issue.
- Import order: `os`, `sys` (stdlib) → `yaml`, `openai` (third-party). Correct per rune.

`tests/test_osaurus_client.py` — 21 tests, full AC2.1–AC2.8 coverage. No findings.
- INFO: `import osaurus_client  # noqa: E402` at bottom of file (line ~284). This is a cosmetic nit carried from QA pass 2. Functionally correct: Python test methods look up module globals at call time (not at class definition time), so the bottom import is in scope before any test method executes. Lint-clean. Accepted — see Justification Review.

`requirements.txt` — `openai>=1.0,<3` inserted correctly between pyyaml and ruff. No findings.

`docs/runes/osaurus.md` — Rune updates accurate and scoped. No findings.

`README.md` — Additive-only updates per update-readme rune. No findings.

`tests/smoke_imports.py` — `("openai", "openai")` entry added consistently with existing pattern. No findings.

#### UI Review
No UI-scope changes.

#### AWS Review
No AWS SDK usage, no AWS infrastructure changes.

#### Security Review
- **Injection** — No SQL, no shell execution, no eval/exec. No injection surface.
- **Credential handling** — API key loaded from gitignored `osaurus.yaml` at runtime; never logged. `type(exc).__name__` in stderr handlers prevents accidental key/title/description leakage. Tests explicitly verify key and title/description absence from stderr (AC2.6). ✓
- **Input validation** — Category matching uses `in` set membership on exact-match strings. No regex, no eval. ✓
- **Bounded I/O** — Single HTTP call per invocation, `timeout=3.0` default passed to SDK constructor. No unbounded blocking. ✓
- **Dependency** — `openai>=1.0,<3` is a well-scoped range covering the stable SDK series. No findings.
- No OWASP Top 10 concerns applicable.

---

### UI Review
No UI-scope changes.

---

### Justification Review

- Finding: INFO: `osaurus_client.py` uses `print(file=sys.stderr)` rather than `logging` (global python rune: "prefer logging over print")
  - Prior-step context: QA pass 2 flagged as I-pass2-1; accepted with analysis — AC2.6 mandates "a single concise line to stderr"; `print(file=sys.stderr)` enables `patch("sys.stderr", ...)` in tests; logging requires handler configuration and could emit additional lines (tracebacks, propagation). No decision.md entry by Implementer (implicit: spec-driven choice).
  - Story-Review decision: **accepted**
  - Story-Review analysis: The global python rune's "prefer logging" guidance is correct for application-level logging. However, AC2.6 imposes a hard constraint — exactly one line, no sensitive content — that `print(file=sys.stderr)` satisfies more directly than a configured logging handler. The module is intentionally thin (one public function, no internal state) and the stderr output is test-verified at the exact-line-count level. Adding a `logging.getLogger(__name__)` with a NullHandler default plus a `logging.StreamHandler(sys.stderr)` per call would introduce more complexity without benefit, and could be mis-configured to emit multi-line output. The print-to-stderr pattern is the correct pragmatic choice for this spec constraint.
  - Propagation: Accepted. Guardrails: If US-3 or a future story extends `osaurus_client.py` to add richer diagnostics (e.g., debug-level context), or if the module grows beyond one public function, switch to `logging.getLogger("osaurus_client")` with a configured handler. Revisit trigger: any Story-Review or Feature-Review that adds a second logging call site to osaurus_client.py.

- Finding: INFO: `import osaurus_client  # noqa: E402` at bottom of test file
  - Prior-step context: QA pass 2 noted as 🔵 nit (I-pass2-nit); not escalated. Lint-clean via noqa. No AC impact.
  - Story-Review decision: **accepted**
  - Story-Review analysis: Functionally correct. Python resolves module-level names at call time; test methods that reference `osaurus_client` work because the import at line ~284 executes before any test method is invoked by pytest. Lint is suppressed correctly. No rune violation. The unconventional placement is a minor readability concern but not a correctness issue.
  - Propagation: Accepted. Guardrails: If the test file is restructured or a new developer is confused, a comment explaining the bottom import (e.g., `# Module-under-test import follows sys.path setup if needed`) would improve clarity. Not required for current story. Revisit trigger: if test discovery breaks or a future developer moves the import.

- Finding: INFO: README.md `openai` not listed as an explicit named package in a Requirements section
  - Prior-step context: QA pass 1 L2 required README update; QA pass 2 marked RESOLVED. README references `requirements.txt` for install and `openai-compatible` appears in the osaurus_client.py Project Structure entry.
  - Story-Review decision: **accepted**
  - Story-Review analysis: The README does not enumerate individual packages — it defers to `requirements.txt` for the full list. The `update-readme` rune requires updating the "dependency list and Project Structure table." The Project Structure entry for osaurus_client.py mentions "openai-compatible" and the optional osaurus note in Requirements covers the new integration. This meets the spirit of the rune in the context of this README's structure. No separate "packages" table exists in the README.
  - Propagation: Accepted permanently. No revisit trigger.

### Backlog Candidates
None. The single pass-1 backlog candidate (`LOW|tests/test_osaurus_client.py|yaml_failure_path|missing exactly-one-line stderr assertion`) was resolved in QA pass 2. No new backlog candidates from Story-Review.

---

## Story Review Decision
- **PASS**
- All AC2.1–AC2.8 satisfied by implementation and verified by tests.
- All rune rules satisfied (osaurus.md and phantom-calendar.md).
- Lint PASS (ruff), tests PASS (191/191).
- No HIGH findings. No MEDIUM findings. No LOW findings.
- All INFO items accepted with documented justification chains (print vs logging, bottom import).
- State files complete and consistent (spec_hash match, status=Done, phase=QA).
- First Story-Review run — two-strike rule not applicable.
