---
phase: Story-Review
spec_hash: '0cff6720f5bf'
status: StoryReviewPassed
blockers: None
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Extend _show_popup(result, config) in sync_job.py: for each unknown block show choose-from-list dialog with integer meeting_type_prep options + Skip.
- If selected, recalculate alarm_time from block start - prep_minutes.
- Return classifications list in popup_response.
- Update run_nightly_sync to pass config to _show_popup.
- Create tests/test_classification_ui.py with 7+ mocked tests.
