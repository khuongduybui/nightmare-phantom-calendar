"""Calendar reader — fetches tomorrow's MSI time blocks and Personal events."""

import os
from datetime import date, datetime, time, timedelta

import pytz

from auth import get_calendar_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PERSONAL_CALENDAR_ID = "duykbui1989@gmail.com"
MSI_CALENDAR_ID = "duy.bui@motorolasolutions.com"
LOCAL_TZ = pytz.timezone("America/New_York")


def get_tomorrow_range() -> tuple[str, str]:
    """Return (start_iso, end_iso) covering all of tomorrow in LOCAL_TZ."""
    tomorrow = date.today() + timedelta(days=1)
    start = LOCAL_TZ.localize(datetime.combine(tomorrow, time.min))
    end = LOCAL_TZ.localize(datetime.combine(tomorrow, time.max))
    return start.isoformat(), end.isoformat()


def get_msi_time_blocks(calendar_id: str = MSI_CALENDAR_ID) -> list[dict]:
    """Return tomorrow's MSI time blocks as [{'start': datetime, 'end': datetime}].

    Events with only an all-day 'date' key are silently skipped.
    Results are sorted by start ascending.
    """
    service = get_calendar_service()
    start, end = get_tomorrow_range()
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
                }
            )

    return sorted(blocks, key=lambda x: x["start"])


def get_personal_events(calendar_id: str = PERSONAL_CALENDAR_ID) -> list[dict]:
    """Return tomorrow's Personal calendar events as [{'title', 'start', 'end'}].

    Events with only an all-day 'date' key are silently skipped.
    Results are sorted by start ascending.
    """
    service = get_calendar_service()
    start, end = get_tomorrow_range()
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
                "title": event.get("summary", "Untitled"),
                "start": datetime.fromisoformat(start_str),
                "end": datetime.fromisoformat(end_str) if end_str else None,
            }
        )

    return sorted(events, key=lambda x: x["start"])
