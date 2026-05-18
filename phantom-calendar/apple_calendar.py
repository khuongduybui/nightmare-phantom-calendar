"""Apple Calendar reader — reads events from macOS Calendar.app via ical-guy CLI."""

import json
import logging
import os
import platform
import shutil
import subprocess
from datetime import date, datetime

import pytz

logger = logging.getLogger(__name__)

# Homebrew installs ical-guy here on Apple Silicon and Intel Macs.
# When the app is launched outside a login shell (launchd, Finder, etc.) the
# process PATH omits /opt/homebrew/bin and /usr/local/bin, so shutil.which
# would return None even though ical-guy is installed.  We probe known paths
# explicitly as a fallback.
_ICAL_GUY_FALLBACK_PATHS = [
    "/opt/homebrew/bin/ical-guy",   # Apple Silicon Homebrew
    "/usr/local/bin/ical-guy",       # Intel Homebrew
]


def _ical_guy_path() -> str | None:
    """Return the absolute path to the ical-guy binary, or None if not found."""
    found = shutil.which("ical-guy")
    if found:
        return found
    for candidate in _ICAL_GUY_FALLBACK_PATHS:
        if shutil.which(candidate) is not None or _is_executable(candidate):
            return candidate
    return None


def _is_executable(path: str) -> bool:
    """Return True if path exists and is executable."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


def is_accessible() -> bool:
    """Return True if ical-guy can read Apple Calendar on this machine.

    Checks: macOS platform, macOS ≥14, ical-guy binary found, probe read succeeds.
    Returns False (never raises) when any check fails.
    """
    try:
        system = platform.system()
        logger.debug("platform.system() = %r", system)
        if system != "Darwin":
            return False

        ver_str = platform.mac_ver()[0]
        logger.debug("macOS version = %r", ver_str)
        if not ver_str or int(ver_str.split(".")[0]) < 14:
            return False

        binary = _ical_guy_path()
        logger.debug("ical-guy binary = %r", binary)
        if binary is None:
            return False

        # Probe: list calendars. stdout is not a TTY (capture_output=True) so
        # ical-guy auto-selects JSON output — do NOT pass --format json here;
        # that flag is only supported by the `events` subcommand and causes a
        # Swift fatalError (exit 133) on `calendars`.
        cmd = [binary, "calendars"]
        logger.debug("probe cmd: %s", cmd)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        logger.debug("probe exit=%d", result.returncode)
        logger.debug("probe stdout=%r", result.stdout[:500])
        if result.stderr.strip():
            logger.debug("probe stderr=%r", result.stderr.strip())
        if result.returncode != 0:
            logger.warning(
                "ical-guy probe failed (exit %d): %s",
                result.returncode,
                result.stderr.strip() or "(no stderr)",
            )
            return False

        json.loads(result.stdout)
        return True
    except Exception as exc:
        logger.debug("is_accessible exception: %s", exc)
        return False


def get_tomorrow_events(
    target_date: date,
    exclude_calendars: list[str] | None = None,
    timezone_str: str = "America/New_York",
) -> list[dict]:
    """Return tomorrow's events from all Apple Calendars as a unified list.

    ical-guy returns times in UTC. This function converts them to the given
    timezone before returning, so callers receive local-time datetimes
    consistent with the rest of the pipeline.

    Each dict has keys: start (datetime), end (datetime), title (str),
    description (str), location (str | None).

    Raises RuntimeError if ical-guy is not accessible or returns an error.
    """
    if not is_accessible():
        raise RuntimeError("Apple Calendar not accessible: ical-guy unavailable")

    binary = _ical_guy_path()
    if binary is None:
        raise RuntimeError("Apple Calendar not accessible: ical-guy not found")

    date_iso = target_date.isoformat()
    args = [
        binary,
        "events",
        "--from",
        date_iso,
        "--exclude-all-day",
        "--format",
        "json",
    ]
    if exclude_calendars:
        args.extend(["--exclude-calendars", ",".join(exclude_calendars)])

    logger.debug("events cmd: %s", args)
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=15,
    )
    logger.debug("events exit=%d", result.returncode)
    logger.debug("events stdout=%r", result.stdout[:1000])
    if result.stderr.strip():
        logger.debug("events stderr=%r", result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"ical-guy events failed: {result.stderr.strip()}")

    try:
        raw_events = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(f"ical-guy returned unparseable output: {exc}") from exc

    events = []
    for event in raw_events:
        if event.get("isAllDay"):
            continue

        start_str = event.get("startDate", "")
        if not start_str:
            continue

        try:
            start_dt = datetime.fromisoformat(start_str)
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"ical-guy returned invalid startDate {start_str!r}: {exc}"
            ) from exc

        # Convert UTC to configured local timezone.
        # ical-guy returns ISO 8601 with UTC offset (e.g. 2026-05-19T14:00:00+00:00).
        # datetime.fromisoformat() produces a tz-aware UTC datetime; convert to local.
        local_tz = pytz.timezone(timezone_str)
        if start_dt.tzinfo is not None:
            start_dt = start_dt.astimezone(local_tz)
        else:
            # Naive datetime — assume UTC, localise.
            start_dt = pytz.utc.localize(start_dt).astimezone(local_tz)

        # Date-filter in local time (a UTC event near midnight may land on a different day).
        if start_dt.date() != target_date:
            continue

        end_str = event.get("endDate", "")
        try:
            end_dt = datetime.fromisoformat(end_str) if end_str else start_dt
        except (ValueError, TypeError):
            end_dt = start_dt

        if end_dt is not start_dt:  # only convert if not already the fallback
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(local_tz)
            else:
                end_dt = pytz.utc.localize(end_dt).astimezone(local_tz)

        events.append(
            {
                "start": start_dt,
                "end": end_dt,
                "title": event.get("title") or "Untitled",
                "description": event.get("notes") or "",
                "location": event.get("location"),
            }
        )

    return sorted(events, key=lambda e: e["start"])
