# What the feature is

Unify all debug and diagnostic output across the entire codebase under the standard `logging` module. This replaces every ad-hoc `print()` pattern — including private `_dbg()` / `_log()` helpers, inline `[DEBUG]` prefixed prints, `[module]` prefixed info/warning prints, and raw `print(..., file=sys.stderr)` error calls — with module-level `logging.getLogger(__name__)` loggers. Entry points (`main.py`, `app.py`) gain a shared logging configuration that routes output to stderr and honours a `PHANTOM_DEBUG` environment variable to enable verbose output.

Affected modules: `sync_job.py`, `compute.py`, `drive_config.py`, `apple_calendar.py`, `calendar_writer.py`, `app.py`, `main.py`, `osaurus_client.py`.

# Why we need it

Tech debt. The codebase accumulated at least five distinct ad-hoc debug patterns across eight modules:
- `sync_job.py` — private `_dbg()` helper writing to stderr + many `[DEBUG]` prints
- `apple_calendar.py` — private `_log()` helper writing to stderr, gated on `PHANTOM_APPLE_DEBUG` env var
- `compute.py` — inline `print(f"[DEBUG] ...")` calls with no helper
- `drive_config.py`, `calendar_writer.py`, `app.py`, `main.py`, `osaurus_client.py` — `[module]` prefixed info/warning/error prints to stdout or stderr

Partial migration of `sync_job.py` alone (deferred from NPC-0014) would leave seven other files inconsistent. A single story covering all eight modules is the correct scope.

# Acceptance Criteria (testable)

**AC1 — No `print()` calls remain in any production module**
Given the migration is complete, when every `.py` file under `phantom-calendar/` (excluding `tests/`) is scanned, then no `print(` calls are present in any production source file.

**AC2 — Every module uses a module-level logger**
Given any migrated module, when its source is read, then exactly one `logger = logging.getLogger(__name__)` declaration appears at module level, and all log calls go through that logger — no ad-hoc helpers (`_dbg`, `_log`, etc.) remain.

**AC3 — Logging levels are appropriate**
Given each former `print()` call, when replaced:
- `[DEBUG]` / verbose detail → `logger.debug()`
- Normal flow milestones (start, completion, config loaded) → `logger.info()`
- Non-fatal anomalies (`WARNING:`) → `logger.warning()`
- Caught exceptions / failures → `logger.error()` or `logger.exception()`

**AC4 — Shared logging bootstrap in entry points**
Given `main.py` and `app.py` are the only entry points, when either starts, then it calls a shared `configure_logging()` helper (or equivalent inline `basicConfig`) that directs output to stderr at `INFO` level by default.

**AC5 — `PHANTOM_DEBUG` env var enables DEBUG output**
Given `PHANTOM_DEBUG=1` is set in the environment, when an entry point starts, then the root logger level is set to `DEBUG`, making verbose output from all modules visible — replacing the old per-module `PHANTOM_APPLE_DEBUG` flag.

**AC6 — Library modules do not configure logging**
Given any module other than `main.py` and `app.py`, when it is imported, then it does not call `logging.basicConfig()`, add handlers, or set logger levels — logging is configured solely by entry points.

**AC7 — Existing tests pass without modification**
Given the migration is applied, when the full test suite is run, then all tests pass without changes to test assertions.
