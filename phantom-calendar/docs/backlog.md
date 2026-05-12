# Phantom Calendar — Backlog

Deferred items from MVP 2 feature definition. Not prioritized.

## Scheduler
- Configurable trigger time (fixed at 9pm in NPC-0004)
- Weekday-only scheduling option
- Retry logic for failed nightly syncs
- System-level scheduling via launchd (instead of in-process APScheduler)

## Confirmation Popup (NPC-0002)
- Configurable behavior for baseline case — option to suppress popup when no new event is needed
- Configurable behavior for no-meetings case — option to suppress popup when calendar is empty
- Snooze / "remind me later" option
- Show full meeting list for tomorrow, not just the first meeting

## Calendar Writer (NPC-0003)
- Undo / manual deletion of a written alarm outside of a sync run

## Menu Bar App (NPC-0005)
- Persist last run state and last alarm time across app restarts
- Custom icon design
- Preferences / settings window

## On-Demand Sync (NPC-0006)
- Keyboard shortcut / hotkey trigger

## Packaging & Distribution
- PyInstaller packaging as .app bundle
- Distribute via drag-to-Applications or DMG

## Future (MVP 3+)
- Location-based travel time: use `locations` config (location name → travel minutes) to adjust prep time based on meeting location
- Client-specific prep overrides: use `client_overrides` config (client name → prep minutes) to override default prep per client
- Replace tkinter popup with native SwiftUI notification
- Google Maps API for live travel time based on event location
- Watch for calendar change events and auto-recompute
- Config editor UI inside the app (instead of editing Google Drive directly)
- Multiple timezone support
- Apple Calendar integration
