---
phase: QA
spec_hash: 'ba1561a5443c'
status: Done
blockers: None
---

## Last Run
- python -m pytest tests/ -v — PASS (202/202)

## Changes Since Last Iteration
- Added `import osaurus_client` to `sync_job.py`.
- Added `_ask_recurring_or_oneshot()` helper for the second dialog.
- Modified `_classify_unknown_blocks`: calls `osaurus_client.suggest_meeting_type` before each dialog (with try/except defence-in-depth); uses suggestion as `default items` when available; shows Recurring/One-shot dialog after non-Skip selection; only appends to `classifications` on Recurring.
- Added `_classify_personal_events()` — mirrors same flow for personal events.
- In `_show_popup`: added personal event classification call after `_prompt_unknown_locations`; personal events passed via `result["personal_events"]`.
- In `run_nightly_sync`: augments `result` with filtered `personal_events` before calling `_show_popup`.
- Updated `test_classification_ui.py`: fixed 2 existing tests for extra Recurring/One-shot dialog; added `TestOsaurusSuggestion` (4 tests) and `TestClassifyPersonalEvents` (5 tests).

## Next Steps
- QA loop then Story-Review loop until both return PASS.
