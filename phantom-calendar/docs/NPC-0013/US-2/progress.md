---
phase: Implementer
spec_hash: '757184e6135b'
status: NotStarted
blockers: 'None'
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized.

## Next Steps
- Create `phantom-calendar/osaurus_client.py` with `suggest_meeting_type(title, description, categories, timeout=3.0)`.
- Use model `"foundation"`, `temperature=0`, `max_tokens=32`, no retry, exception → `None`.
- Validate model response against `categories`; non-match → `None`.
- Add `openai>=1.0,<3` to `phantom-calendar/requirements.txt`; install in venv via `uv pip install -r requirements.txt`.
- Add `tests/test_osaurus_client.py` covering: happy path (suggestion in list), invalid suggestion, connection error, timeout, generic exception, missing/unparseable `osaurus.yaml`, single-call assertion (no retry), no-leak assertion (api_key/title/description absent from stderr).
- Update `docs/runes/osaurus.md` rule `osaurus-openai-client` to reflect that `openai` is now a runtime dependency in this repo.
- Run full test suite via `build/tests.sh`.
