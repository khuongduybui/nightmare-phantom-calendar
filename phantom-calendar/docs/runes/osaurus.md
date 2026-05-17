# Rune: osaurus

Component-scoped rules for using the osaurus local AI server in `phantom-calendar/`.
Apply during Implementer, QA, Story-Review, and Feature-Review phases.

---

## Rule: osaurus-config-location

**When:** Any code reads the osaurus server URL or API key.
**Action:** Always load both values from `phantom-calendar/osaurus.yaml`. Never hardcode the server address or API key. Schema:
```yaml
server: http://127.0.0.1:1337
api_key: osk-v1.<token>
```
`osaurus.yaml` is gitignored — never commit it. A template file may be provided (e.g. `credentials.json.template` pattern).
**Owner:** Implementer, Story-Review

---

## Rule: osaurus-openai-client

**When:** Any code calls the osaurus server.
**Action:** Use the `openai` Python client with the osaurus server as a custom base URL:
```python
from openai import OpenAI
client = OpenAI(base_url=f"{server}/v1", api_key=api_key)
```
`server` must have any trailing slash stripped before appending `/v1`. The `openai` package is **not** in `requirements.txt` (it is a dev/test dependency only); install it separately with `uv pip install openai`.
**Owner:** Implementer

---

## Rule: osaurus-model-selection

**When:** Any script or module chooses a model to run on osaurus.
**Action:** Prefer accepting a `--model` CLI argument or `model` parameter. When no model is specified, enumerate available models via `client.models.list()` and:
- If the default model `"foundation"` is in the list, use it automatically.
- If exactly one model is available (and it's not `"foundation"`), use it automatically.
- If multiple models are available, present a numbered list and prompt the user to select.
- If no models are available, exit with a clear error message to stderr.

The default model name is `"foundation"`. Store it as a module-level constant (`DEFAULT_MODEL = "foundation"`) so it can be overridden without hunting through logic.
**Owner:** Implementer

---

## Rule: osaurus-prompt-design

**When:** Any feature uses osaurus for LLM inference on calendar data.
**Action:** Use `temperature=0` for deterministic classification tasks. Include a system prompt that:
1. States the role explicitly (e.g. "You are a calendar event classifier").
2. Provides the full list of valid output values inline.
3. Instructs the model to respond with **only** the chosen value — no explanation, no punctuation.

Set `max_tokens` to a small value (e.g. 32) to avoid runaway completions.
**Owner:** Implementer, QA

---

## Rule: osaurus-not-in-production-pipeline

**When:** Any feature proposal routes live sync traffic through osaurus.
**Action:** Osaurus is a local server — it requires the user's machine to be running the osaurus process. Do **not** call osaurus from `sync_job.py` or `scheduler.py` as part of the nightly pipeline. Osaurus integration is limited to:
- Developer test scripts (e.g. `test_classify.py`)
- Optional interactive classification flows triggered explicitly by the user

If AI-assisted classification is needed in the live sync, design it as an opt-in step with a graceful fallback when the server is unavailable.
**Owner:** Feature-Review, QA

---
