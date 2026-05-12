---
phase: Story-Review
spec_hash: '77dde19595b0'
status: StoryReviewPassed
blockers: None
---

## Last Run
- 2026-05-12: Implemented US-3 — created app.py, main.py, tests/test_main.py. 1/1 unit test passes on Python 3.14.4. ACs 3.5–3.7 require manual verification.

## Changes Since Last Iteration
- Created app.py: PhantomCalendarApp(rumps.App) with name, title, quit_button, Run now menu item stub. No scheduler import.
- Created main.py: calls get_credentials() before app launch, catches FileNotFoundError → stderr message + sys.exit(1).
- Created tests/test_main.py: mocks get_credentials raising FileNotFoundError, asserts exit code 1, stderr contains 'Error' and 'credentials.json', no traceback, app not launched.

## Next Steps
- Create app.py with PhantomCalendarApp(rumps.App): name='Phantom Calendar', title='⏰', quit_button='Quit', Run now stub. NO scheduler import.
- Create main.py: call get_credentials() first, catch FileNotFoundError → print to stderr + sys.exit(1), then invoke app.
- Create tests/test_main.py: mock get_credentials raising FileNotFoundError, assert sys.exit(1) and stderr contains readable message.
- Manual verify (after H-1 through H-4 complete): python main.py shows ⏰ in menu bar, dropdown shows Run now + Quit, Quit exits cleanly.
