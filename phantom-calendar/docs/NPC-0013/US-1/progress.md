---
phase: QA
spec_hash: '757184e6135b'
status: Done
blockers: None
---

## Last Run
- python -m pytest tests/ -v — PASS (170/170)

## Changes Since Last Iteration
- Extended `get_msi_time_blocks()` to return `title` (default `"Untitled"`) and `description` (default `""`) per block.
- Extended `get_personal_events()` to return `description` (default `""`) per event; changed `title` default from `"Untitled"` (via `event.get("summary", "Untitled")`) to `event.get("summary") or "Untitled"` for consistency with MSI blocks (treats empty string summary as Untitled).
- Updated `test_get_msi_time_blocks_returns_start_end_only` to assert new fields are present.
- Added 7 new test cases covering: MSI title present, MSI title absent, MSI description present, MSI description absent, personal description present, personal description absent, personal title absent.
- All existing tests pass unchanged (including test_compute.py).

## Next Steps
- QA loop then Story-Review loop until both return PASS.
