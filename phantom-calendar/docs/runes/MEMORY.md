# Memory Index — phantom-calendar

## Global

Always load these first. Universal policy — applies to all components.

| File | Component | Description |
|------|-----------|-------------|
| [phantom-calendar](phantom-calendar.md) | phantom-calendar | Project-wide rules: test discovery, manual tests, README, credential gitignore, Python 3.14 compat, venv/uv conventions, icon design, no-tkinter-in-rumps, no-heredoc, local state gitignore, logging module conventions (module-level logger, entry-point-only basicConfig, PHANTOM_DEBUG env var, assertLogs in tests) |

## Components

| File | Component | Description |
|------|-----------|-------------|
| [ical-guy](ical-guy.md) | ical-guy | ical-guy CLI: binary discovery, subcommand quirks (`calendars` probe no `--format json`, `events` single-day `--from` only), JSON field mapping, PATH fallback for non-login shells |
| [osaurus](osaurus.md) | osaurus | osaurus local AI server config, client usage, and suggestion flow |
