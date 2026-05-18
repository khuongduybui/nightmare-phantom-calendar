"""Apple Calendar reader — reads events from macOS Calendar.app via ical-guy CLI."""

import json
import platform
import shutil
import subprocess
from datetime import date, datetime


def is_accessible() -> bool:
    """Return True if ical-guy can read Apple Calendar on this machine.

    Checks: macOS platform, macOS ≥14, ical-guy in PATH, probe read succeeds.
    Returns False (never raises) when any check fails.
    """
    try:
        if platform.system() != "Darwin":
            return False

        ver_str = platform.mac_ver()[0]
        if not ver_str or int(ver_str.split(".")[0]) < 14:
            return False

        if shutil.which("ical-guy") is None:
            return False

        result = subprocess.run(
            ["ical-guy", "calendars", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False

        json.loads(result.stdout)
        return True
    except Exception:
        return False


def get_tomorrow_events(
    target_date: date,
    exclude_calendars: list[str] | None = None,
) -> list[dict]:
    """Return tomorrow's events from all Apple Calendars as a unified list.

    Each dict has keys: start (datetime), end (datetime), title (str),
    description (str), location (str | None).

    Raises RuntimeError if ical-guy is not accessible or returns an error.
    """
    if not is_accessible():
        raise RuntimeError("Apple Calendar not accessible: ical-guy unavailable")

    date_iso = target_date.isoformat()
    args = [
        "ical-guy",
        "events",
        "--from",
        date_iso,
        "--to",
        date_iso,
        "--exclude-all-day",
        "--format",
        "json",
    ]
    if exclude_calendars:
        args.extend(["--exclude-calendars", ",".join(exclude_calendars)])

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=15,
    )
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

        if start_dt.date() != target_date:
            continue

        end_str = event.get("endDate", "")
        try:
            end_dt = datetime.fromisoformat(end_str) if end_str else start_dt
        except (ValueError, TypeError):
            end_dt = start_dt

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
