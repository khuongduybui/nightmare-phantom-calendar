---
phase: Planner
spec_hash: 'ba1561a5443c'
status: Draft
---

# NPC-0013 — AI-assisted meeting classification via osaurus

## Clarifications from Codebase

| feature.md term | Codebase mapping |
|---|---|
| Unknown work (MSI) block | Item appended to `unknown_blocks` in `compute_alarm()` (compute.py) when `match_block_to_meeting()` returns `None`. Origin: `get_msi_time_blocks()` in `calendar_reader.py`. |
| Unclassified personal event | Any item in the list returned by `get_personal_events()` in `calendar_reader.py`, excluding events whose title contains `"Alarm"` (already filtered in `compute_alarm()`). |
| Meeting type | A key of `config["meeting_type_prep"]` (config.yaml). |
| Classification dialog | Existing osascript `choose from list` in `_classify_unknown_blocks()` (sync_job.py). |
| One-shot vs recurring prompt | New osascript `display dialog` with buttons `Recurring` / `One-shot`, fired after type selection. |
| Drive config recurring_meetings | `config["recurring_meetings"]`, written via `drive_config.append_recurring_meetings(classifications, config)`. |
| osaurus | Local OpenAI-compatible server. Config in `phantom-calendar/osaurus.yaml`: `server`, `api_key`, `default_module` (fallback `"foundation"`). |
| Sync popup | The osascript dialog flow in `_show_popup()` in sync_job.py. |
| Baseline match | `result["is_baseline"] is True` from `compute_alarm()`. |
| Pre-selected default item | `default items {{"<name>"}}` argument to the osascript `choose from list` command. |

**Codebase-reality flags** (none of feature.md is edited):
- `get_msi_time_blocks()` currently returns only `{"start", "end"}` per block. feature.md AC1 requires also returning `title` and `description` — this is a real new field, not a rename.
- `get_personal_events()` already returns `title`; only `description` is genuinely new.
- The current code has **no personal-event type-classification step** — feature.md AC10 introduces one.

---

## User Stories (ordered by dependency)

### US-1 — Extend calendar readers to return title and description

Foundational data plumbing. No new behavior is observable by the end user; downstream stories depend on these fields.

**Scope**
- `get_msi_time_blocks()` must return each block as `{"start", "end", "title", "description"}`. `title` defaults to `"Untitled"` when the API event has no `summary`. `description` defaults to `""` when the API event has no `description`.
- `get_personal_events()` must return each event as `{"title", "start", "end", "location", "description"}`. `description` defaults to `""`.
- All existing call sites must continue to work — only additive fields.
- Tests added for both new fields with present, missing, and empty cases.

**Acceptance Criteria**
- AC1.1 — `get_msi_time_blocks()` returns `title` and `description` for every block, with the documented defaults when absent.
- AC1.2 — `get_personal_events()` returns `description` for every event, defaulting to `""` when absent.
- AC1.3 — Existing tests in `tests/test_calendar_reader.py` continue to pass without modification of asserted shape, except for any test that asserts the keys returned (which must be updated).
- AC1.4 — New unit tests cover: summary present, summary absent (→ `"Untitled"`), description present, description absent (→ `""`).
- AC1.5 — `compute_alarm()` is not modified; downstream code that does not need the new fields is unaffected (verified by passing the existing `tests/test_compute.py`).

Maps to feature AC1, AC2.

**File touch list (US-1)**
- `phantom-calendar/calendar_reader.py`
- `phantom-calendar/tests/test_calendar_reader.py`

**Definition of Done (US-1)**
- All tests in `tests/test_calendar_reader.py` pass.
- Full test suite (`build/tests.sh`) passes.

---

### US-2 — osaurus suggestion client module

A new isolated module that wraps the osaurus call. No integration into the sync flow yet — that lands in US-3.

**Scope**
- New module: `phantom-calendar/osaurus_client.py`.
- Public function:
  ```
  suggest_meeting_type(
      title: str,
      description: str,
      categories: list[str],
      timeout: float = 3.0,
  ) -> str | None
  ```
  - Loads `phantom-calendar/osaurus.yaml` lazily and reads `server`, `api_key`, and `default_module` (fallback `"foundation"`).
  - Builds an `openai.OpenAI(base_url=f"{server}/v1", api_key=api_key)` client.
  - Issues one `chat.completions.create(...)` request with model read from `default_module`, `temperature=0`, `max_tokens=32`, and the supplied timeout.
  - System prompt instructs the model to return exactly one category from `categories`, no punctuation, no explanation.
  - User message: `"Title: {title}\nDescription: {description}"`.
  - Validates the response text (stripped) against `categories`. If the stripped response exactly matches one of `categories`, return that category. Otherwise return `None`.
  - On **any** exception (connection refused, timeout, HTTP error, malformed response), catch it and return `None`. No retry.
  - On failure, write a single concise line to `stderr`: `"[osaurus_client] WARNING: <short error class name>"`. **Do not** include the API key, the response body, the event title, or the description in any stderr or log output.
- Add `openai>=1.0,<3` to `phantom-calendar/requirements.txt`.
- New test module: `phantom-calendar/tests/test_osaurus_client.py`.

**Acceptance Criteria**
- AC2.1 — `suggest_meeting_type(...)` issues exactly one chat completion with model read from `osaurus.yaml` key `default_module` (fallback `"foundation"`), `temperature=0`, `max_tokens=32`, and the timeout parameter forwarded to the openai client.
- AC2.2 — Returns the matched category string when the model response (stripped) exactly matches one of `categories`.
- AC2.3 — Returns `None` when the model response does not match any category in `categories`.
- AC2.4 — Returns `None` when the openai client raises any exception (test cases: connection error, timeout, generic exception).
- AC2.5 — No retry: the openai client is invoked exactly once per call to `suggest_meeting_type`, including on failure paths.
- AC2.6 — On failure, exactly one line is written to stderr and the line does not contain the `api_key` value, the event title, the event description, or any portion of the response body other than (optionally) the exception class name.
- AC2.7 — Loading `osaurus.yaml` failure (file missing or unparseable) is treated as failure → returns `None` and logs to stderr.
- AC2.8 — Tests use `unittest.mock.patch` on `openai.OpenAI` (or the `chat.completions.create` call) — no live network calls.

Maps to feature AC3, AC5 (partial), AC12 (partial), AC13, AC15 (partial), AC16.

**File touch list (US-2)**
- `phantom-calendar/osaurus_client.py` (new)
- `phantom-calendar/requirements.txt`
- `phantom-calendar/tests/test_osaurus_client.py` (new)

**Definition of Done (US-2)**
- All tests in `tests/test_osaurus_client.py` pass.
- `python -c "from osaurus_client import suggest_meeting_type"` succeeds in the venv.
- Full test suite passes.

---

### US-3 — Wire suggestion + recurring/one-shot dialogs into the sync popup

Integration story. Adds AI-assisted defaults to the existing classification dialog and introduces personal-event type classification + the one-shot/recurring branch.

**Scope**

1. **MSI unknown block classification (modify `_classify_unknown_blocks`)**
   - Build the list of category names from `config["meeting_type_prep"]` keys whose value is an `int` (preserves existing behavior — travel+N entries excluded from this dialog).
   - Before each block's `choose from list` dialog, call `osaurus_client.suggest_meeting_type(title, description, category_names)` where `title` and `description` come from the block (now populated by US-1).
   - If `suggest_meeting_type` returns a non-`None` value, set the dialog's `default items` to `{"<suggestion>"}`. Otherwise, keep the existing `{"Skip (keep default)"}` default.
   - After the user selects a non-Skip type, show a second osascript dialog asking `"Save this for future runs?"` with buttons `Recurring` / `One-shot` (default `Recurring`).
   - If `Recurring`: append the entry to `classifications` (existing behavior — alarm is recomputed and the entry is later written to Drive config).
   - If `One-shot`: recompute the alarm exactly as the recurring path does, but **do not** append to `classifications`. Track the prep time in the alarm calculation only.
   - On user cancel of the second dialog: treat as `One-shot` (alarm updated, not saved).

2. **Personal event type classification (new `_classify_personal_events` function in `sync_job.py`)**
   - Inputs: `personal_events` (already filtered to exclude alarm events), `config`, `current_alarm`.
   - For each personal event (`title` is always present — `get_personal_events()` already defaults to `"Untitled"` via `event.get("summary", "Untitled")`), call `osaurus_client.suggest_meeting_type()` exactly as for MSI blocks.
   - Show the same `choose from list` dialog. If the user picks a non-Skip type, show the Recurring/One-shot dialog.
   - `Recurring`: append the entry to `classifications` using the existing entry shape (start_time, meeting_type, prep_minutes).
   - `One-shot`: update the alarm only; do not append.
   - Returns `(classifications_delta, updated_alarm_time)`.
   - Wired into `_show_popup` after `_classify_unknown_blocks` and after `_prompt_unknown_locations`. Skipped on baseline (`result["is_baseline"] is True`) and on no-meetings.

3. **Popup orchestration**
   - In `_show_popup`, the order remains: `_classify_unknown_blocks` → `_prompt_unknown_locations` → `_classify_personal_events`. All three are skipped on baseline.
   - The summary lines section continues to display each unknown block's classification status.

4. **Wiring constraints**
   - The `osaurus_client.suggest_meeting_type` call must run in the same background thread as the existing classification (sync_job pipeline), not on the main thread.
   - The osaurus client must never raise out of `_classify_unknown_blocks` or `_classify_personal_events` — wrap each call in `try/except Exception` as a defence-in-depth (the client already catches internally; this is belt-and-suspenders so a sync run cannot be killed by a refactor of the client).

**Acceptance Criteria**
- AC3.1 — When `_classify_unknown_blocks` runs and `suggest_meeting_type` returns a valid category, that category appears as the `default items` value in the osascript `choose from list` command for that block.
- AC3.2 — When `suggest_meeting_type` returns `None`, the dialog's `default items` is `{"Skip (keep default)"}` (unchanged from current behavior).
- AC3.3 — After the user selects any non-Skip type, a second osascript `display dialog` is invoked with buttons containing both `"Recurring"` and `"One-shot"`.
- AC3.4 — Selecting `Recurring` results in an entry being appended to the returned `classifications` list with keys `start_time`, `meeting_type`, `prep_minutes` (and `location` when provided).
- AC3.5 — Selecting `One-shot` results in the alarm time being recomputed but **no** entry being appended to the returned `classifications` list.
- AC3.6 — A new `_classify_personal_events` function exists, is called from `_show_popup` for non-baseline non-empty results, and follows the same suggest → select → Recurring/One-shot flow.
- AC3.7 — `_show_popup` skips both `_classify_unknown_blocks` and `_classify_personal_events` when `result["is_baseline"] is True` or `result["first_meeting_name"] is None`.
- AC3.8 — When `suggest_meeting_type` raises an exception (mocked), `_classify_unknown_blocks` and `_classify_personal_events` still open their dialogs with no pre-selection and the sync pipeline completes.
- AC3.9 — Unit tests cover: suggestion pre-selected, suggestion absent, user accepts suggestion (Recurring), user accepts suggestion (One-shot), user overrides suggestion, user picks Skip, personal-event happy path, exception in suggest call.
- AC3.10 — Existing tests in `tests/test_classification_ui.py` and `tests/test_classification_write.py` pass after updates to account for the new dialog and the new function.
- AC3.11 — `run_calendar_write` and the existing `append_recurring_meetings` call site in `sync_job.run_nightly_sync` are unchanged — they receive the (already filtered) `classifications` list containing only Recurring entries.

Maps to feature AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC10, AC11, AC12, AC14.

**File touch list (US-3)**
- `phantom-calendar/sync_job.py`
- `phantom-calendar/tests/test_classification_ui.py`
- `phantom-calendar/tests/test_classification_write.py`
- `phantom-calendar/tests/test_sync_job.py`

**Definition of Done (US-3)**
- All ACs above and all referenced feature ACs verified.
- Full test suite passes.
- `osaurus_client` is not referenced from `scheduler.py` or from any path reachable when the scheduler triggers a sync without user interaction (it lives only in the popup-driven classification helpers, which are no-ops in non-interactive paths).

---

## Acceptance Criteria (feature-wide)

- **FW1 — No new dependencies on remote services.** Beyond the existing Google Calendar / Drive APIs, the only new outbound traffic is to `http://127.0.0.1:1337` (osaurus, local).
- **FW2 — Graceful degradation.** With osaurus stopped, the entire feature degrades to current behavior: classification dialog opens with the existing default; no error visible to the user; one stderr line per failed call.
- **FW3 — No regressions in existing classification.** All existing `tests/test_classification_*.py` and `tests/test_sync_job.py` tests must still pass (after necessary updates for the new dialog).
- **FW4 — Tests run offline.** No test in the suite issues a real HTTP request to osaurus. All osaurus interactions are mocked.

---

## Constraints

- **No tkinter** in `sync_job.py` or any path reachable from a rumps callback — osascript only (per `phantom-calendar.md` rune `no-tkinter-in-rumps-process`).
- **No bare `python` / `pip`** — use `uv run` / `uv pip` per rune `venv-and-uv-conventions`.
- **No hardcoded osaurus URL or API key** — always loaded from `osaurus.yaml` per rune `osaurus-config-location`.
- **Model name** for osaurus calls is read from `osaurus.yaml` key `default_module` (fallback `"foundation"`) per rune `osaurus-model-selection`.
- **No retry** of the osaurus call.
- **API key, event title, event description, and full response body** must not appear in stderr or any log.
- **`osaurus.yaml`** must remain in `.gitignore`.
- **`requirements.txt`** must include `openai` (it is **not** a dev-only dependency in this feature — the production sync pipeline uses it).

> **Rune scope adjustment** — the `osaurus-openai-client` rune previously stated `openai` is a dev/test dependency only. This feature promotes it to a production dependency; the rune will be updated as part of US-2's Definition of Done (or by the Feature-Review step).

---

## Non-goals

(unchanged from feature.md)

- Batch osaurus calls
- Caching osaurus responses
- Calling osaurus from the unattended nightly scheduler path
- Replacing the osascript dialogs with a native UI
- Classifying the baseline alarm event
- Auto-detecting Google Calendar recurrence to bypass the one-shot/recurring prompt
- Changes to `osaurus.yaml` format or location

---

## Definition of Done (feature-wide)

- All three US Definitions of Done satisfied.
- `build/tests.sh` runs green (entire suite, including new tests).
- `requirements.txt` includes `openai`.
- The `osaurus.md` rune's `osaurus-openai-client` Rule is updated to reflect that `openai` is now a runtime (production) dependency in this repo, and `osaurus-not-in-production-pipeline` is updated to allow the popup-driven, user-interactive classification path while still excluding the unattended scheduler path.
- `README.md` is updated to mention the new AI suggestion behavior (see rune `update-readme`).
- Manual test entry added to `build/manual_tests.md` (see rune `update-manual-tests-md`) covering: osaurus running with a suggestion accepted (Recurring), osaurus running with a suggestion overridden, osaurus stopped (fallback behavior).

---

## Parallelization Analysis

| Story | Independent of | Reason |
|---|---|---|
| US-1 | US-2 | Different files (`calendar_reader.py` vs `osaurus_client.py`). No shared state. No dependency. |
| US-2 | US-1 | Same as above. |
| US-3 | — | Depends on US-1 (needs `title`/`description` on blocks/events) and US-2 (needs `suggest_meeting_type`). |

**Parallel-safe pairs:** `{US-1, US-2}` may run concurrently in separate task worktrees.
**Strict ordering:** US-3 must wait for both US-1 and US-2 to merge.

---

## Proposed Schema Changes

None. `config.yaml` shape is unchanged. No DB.

---

## Proposed Architecture Changes

One new module: **`phantom-calendar/osaurus_client.py`** — isolated wrapper around the `openai` SDK against the local osaurus server. Used only by `sync_job.py` (popup-driven flows). Not imported from `scheduler.py`, `app.py`, `main.py`, or `compute.py`.

```
sync_job._show_popup
   ├── _classify_unknown_blocks ──┐
   │                              ├──► osaurus_client.suggest_meeting_type ──► local osaurus HTTP server
   └── _classify_personal_events ─┘                                            (config in osaurus.yaml)
```

---

## File Touch List (feature-wide)

| File | Story | New? |
|---|---|---|
| `phantom-calendar/calendar_reader.py` | US-1 | edit |
| `phantom-calendar/tests/test_calendar_reader.py` | US-1 | edit |
| `phantom-calendar/osaurus_client.py` | US-2 | **new** |
| `phantom-calendar/requirements.txt` | US-2 | edit |
| `phantom-calendar/tests/test_osaurus_client.py` | US-2 | **new** |
| `phantom-calendar/sync_job.py` | US-3 | edit |
| `phantom-calendar/tests/test_classification_ui.py` | US-3 | edit |
| `phantom-calendar/tests/test_classification_write.py` | US-3 | edit |
| `phantom-calendar/tests/test_sync_job.py` | US-3 | edit |
| `phantom-calendar/docs/runes/osaurus.md` | US-2 DoD / Feature-Review | edit |
| `phantom-calendar/README.md` | Feature-Review | edit |
| `phantom-calendar/build/manual_tests.md` | Feature-Review | edit |

No files outside `phantom-calendar/` are touched.
