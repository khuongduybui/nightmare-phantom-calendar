---
phase: Implementer
spec_hash: 'ba1561a5443c'
status: NotStarted
blockers: 'US-1, US-2'
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized.

## Next Steps
- In `_classify_unknown_blocks`: call `osaurus_client.suggest_meeting_type(block["title"], block["description"], category_names)` before each dialog; set osascript `default items` to the suggestion if returned, else keep `"Skip (keep default)"`.
- After non-Skip selection, show `display dialog` with buttons `Recurring` / `One-shot` (default `Recurring`); cancel → treat as `One-shot`.
- `Recurring` path: append to `classifications` list (existing flow writes it to Drive config).
- `One-shot` path: recompute alarm only — do not append.
- Add `_classify_personal_events(personal_events, config, current_alarm)` mirroring the same suggest → select → Recurring/One-shot flow. Wire into `_show_popup` after `_prompt_unknown_locations`. Skip on baseline / no-meetings.
- Wrap each `suggest_meeting_type` call in `try/except Exception` as defence-in-depth.
- Update existing tests; add new tests for: suggestion pre-selected, suggestion absent, Recurring path, One-shot path, override, Skip, personal-event path, exception during suggest.
- Verify scheduler.py and app.py paths do not import `osaurus_client`.
- Run full test suite via `build/tests.sh`.
