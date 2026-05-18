---
component: ical-guy
applies-to:
  - phantom-calendar/apple_calendar.py
  - phantom-calendar/tests/test_apple_calendar.py
description: |
  ical-guy CLI integration for Apple Calendar reads. Covers binary discovery,
  subcommand quirks, output format, and subprocess invocation patterns.
tags: [layer/cli, tech/pytest, domain/apple-calendar]
---

# Rune: ical-guy

Rules and notes for `apple_calendar.py` and its tests.

---

## Rules

- Install: `brew install itspriddle/brews/ical-guy` (tap required). Binary name is `ical-guy` (with hyphen); installed by Homebrew into `/opt/homebrew/bin/ical-guy` (Apple Silicon) or `/usr/local/bin/ical-guy` (Intel).
- Requires macOS 14 (Sonoma)+. Gate every code path behind `platform.system() == "Darwin"` and `int(platform.mac_ver()[0].split(".")[0]) >= 14`.
- Never use bare `"ical-guy"` in `subprocess.run`. Always call `_ical_guy_path()` first; it falls back to known Homebrew paths when the process `PATH` omits `/opt/homebrew/bin` (launchd / Finder launches).
- Probe accessibility with `ical-guy calendars` (no `--format json`). `--format json` is **only valid for the `events` subcommand** — passing it to `calendars` causes a Swift `fatalError` and exit 133.
- Query events for a single day with `--from {date_iso}` only. Do **not** add `--to` for single-day queries.
- Always pass `--exclude-all-day` to the `events` subcommand; defensive-filter `isAllDay == True` in Python too.
- All `subprocess.run` calls: `capture_output=True, text=True, timeout=15`. Raise `RuntimeError` on non-zero exit — never swallow silently.
- `description` field in the canonical event dict = `event.get("notes") or ""` (JSON field is `notes`, not `description`).
- `endDate` may be absent; fall back to `start_dt` when missing or unparseable.
- Enable verbose logging with `PHANTOM_APPLE_DEBUG=1`; all `_dbg()` calls are gated behind this env var.

---

## Notes

- **JSON output auto-detection**: when stdout is not a TTY (`capture_output=True`), ical-guy auto-selects JSON — no `--format json` needed for `calendars`. The `events` subcommand still requires it explicitly.
- **PATH issue**: apps launched outside a login shell (launchd, Finder, VS Code Run button) inherit a minimal `PATH` that omits `/opt/homebrew/bin`. `shutil.which("ical-guy")` returns `None` in those contexts. `_ical_guy_path()` probes the known Homebrew locations directly via `os.path.isfile` + `os.access(…, X_OK)`.
- **Event JSON fields** used in `apple_calendar.py`:

  | JSON field | Dict key | Notes |
  |---|---|---|
  | `title` | `title` | Falls back to `"Untitled"` when null |
  | `startDate` | `start` | ISO 8601; parse with `datetime.fromisoformat()` |
  | `endDate` | `end` | May be absent; falls back to `start_dt` |
  | `notes` | `description` | May be null; coerced to `""` |
  | `location` | `location` | May be null; kept as `None` |
  | `isAllDay` | — | Filtered out; not passed to compute |
  | `id` | — | Not used (CalDAV UID); only relevant if write-back ever added |

- **Exclusion**: `--exclude-calendars "Name1,Name2"` (comma-separated, single argument). Driven by `config["apple_exclude_calendars"]` (list, default `[]`).
- **Test mocks**: `subprocess.run`, `shutil.which`, `platform.system`, `platform.mac_ver` — all must be mocked in `test_apple_calendar.py`. Never call the real binary from unit tests.
- **Debug**: `PHANTOM_APPLE_DEBUG=1 python main.py` prints every command + exit code + stdout/stderr prefix to stderr.
