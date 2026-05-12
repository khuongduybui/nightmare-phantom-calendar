---
phase: Implementer
spec_hash: '77dde19595b0'
status: NotStarted
blockers: US-1, US-2
---

## Last Run
- N/A

## Changes Since Last Iteration
- State files initialized by Planner.

## Next Steps
- Create app.py with PhantomCalendarApp(rumps.App): name='Phantom Calendar', title='⏰', quit_button='Quit', Run now stub. NO scheduler import.
- Create main.py: call get_credentials() first, catch FileNotFoundError → print to stderr + sys.exit(1), then invoke app.
- Create tests/test_main.py: mock get_credentials raising FileNotFoundError, assert sys.exit(1) and stderr contains readable message.
- Manual verify (after H-1 through H-4 complete): python main.py shows ⏰ in menu bar, dropdown shows Run now + Quit, Quit exits cleanly.
