"""Calendar reader — fetches tomorrow's MSI time blocks and Personal events."""

import os
from datetime import date, datetime, time, timedelta

import pytz

from auth import get_calendar_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PERSONAL_CALENDAR_ID = "duykbui1989@gmail.com"
MSI_CALENDAR_ID = "duy.bui@motorolasolutions.com"
LOCAL_TZ = pytz.timezone("America/New_York")


def get_tomorrow_range(target_date: "date | None" = None) -> tuple[str, str]:
    """Return (start_iso, end_iso) covering the target date (default: tomorrow) in LOCAL_TZ."""
    day = target_date if target_date is not None else date.today() + timedelta(days=1)
    start = LOCAL_TZ.localize(datetime.combine(day, time.min))
    end = LOCAL_TZ.localize(datetime.combine(day, time.max))
    return start.isoformat(), end.isoformat()


def get_msi_time_blocks(
    calendar_id: str = MSI_CALENDAR_ID,
    target_date: "date | None" = None,
) -> list[dict]:
    """Return MSI time blocks for target_date (default: tomorrow).

    Events with only an all-day 'date' key are silently skipped.
    Results are sorted by start ascending.
    """
    service = get_calendar_service()
    start, end = get_tomorrow_range(target_date)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    blocks = []
    for event in result.get("items", []):
        start_str = event.get("start", {}).get("dateTime")
        end_str = event.get("end", {}).get("dateTime")
        if start_str and end_str:
            blocks.append(
                {
                    "start": datetime.fromisoformat(start_str),
                    "end": datetime.fromisoformat(end_str),
                    "title": event.get("summary") or "Untitled",
                    "description": event.get("description") or "",
                }
            )

    return sorted(blocks, key=lambda x: x["start"])


def get_personal_events(
    calendar_id: str = PERSONAL_CALENDAR_ID,
    target_date: "date | None" = None,
) -> list[dict]:
    """Return Personal calendar events for target_date (default: tomorrow).

    Returns [{'title', 'start', 'end', 'location', 'description'}].
    Events with only an all-day 'date' key are silently skipped.
    Results are sorted by start ascending.
    """
    service = get_calendar_service()
    start, end = get_tomorrow_range(target_date)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for event in result.get("items", []):
        start_str = event.get("start", {}).get("dateTime")
        if not start_str:
            continue
        end_str = event.get("end", {}).get("dateTime")
        events.append(
            {
                "title": event.get("summary") or "Untitled",
                "start": datetime.fromisoformat(start_str),
                "end": datetime.fromisoformat(end_str) if end_str else None,
                "location": event.get("location") or None,
                "description": event.get("description") or "",
            }
        )

    return sorted(events, key=lambda x: x["start"])
