"""Calendar writer — writes alarm events to Google Calendar."""

import logging
import os
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

import pytz

from auth import get_calendar_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALARM_TAG = "phantom-calendar-alarm"


def get_tomorrow_range(timezone_str: str) -> tuple[str, str]:
    """Return (start_iso, end_iso) covering all of tomorrow in the given timezone.

    Returns ISO 8601 strings with timezone offset (not UTC Z suffix).
    """
    tz = pytz.timezone(timezone_str)
    tomorrow = date.today() + timedelta(days=1)
    start = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0))
    end = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59))
    return start.isoformat(), end.isoformat()


def get_existing_alarm_for_tomorrow(
    service, calendar_id: str, timezone_str: str
) -> list[dict]:
    """Return all alarm events previously written by this system for tomorrow.

    Queries by ALARM_TAG in description. Returns [] if none found.
    """
    start, end = get_tomorrow_range(timezone_str)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            q=ALARM_TAG,
            singleEvents=True,
        )
        .execute()
    )
    return result.get("items", [])


def delete_alarm_event(service, calendar_id: str, event_id: str) -> None:
    """Delete a specific calendar event by ID."""
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def write_alarm_event(
    service,
    calendar_id: str,
    alarm_time: datetime,
    meeting_name: str,
    timezone_str: str,
    prep_minutes: int,
) -> dict:
    """Write an alarm event to the calendar.

    Duration = prep_minutes so the alarm is back-to-back with the meeting.
    The event is identifiable by ALARM_TAG in its description.
    """
    end_time = alarm_time + timedelta(minutes=prep_minutes)
    event = {
        "summary": f"⏰ Alarm — {meeting_name}",
        "description": ALARM_TAG,
        "start": {
            "dateTime": alarm_time.isoformat(),
            "timeZone": timezone_str,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": timezone_str,
        },
    }
    return service.events().insert(calendarId=calendar_id, body=event).execute()


def get_baseline_instance_for_tomorrow(
    service, calendar_id: str, baseline_event_id: str, timezone_str: str
) -> dict | None:
    """Return tomorrow's occurrence of the baseline recurring event, or None."""
    start, end = get_tomorrow_range(timezone_str)
    result = (
        service.events()
        .instances(
            calendarId=calendar_id,
            eventId=baseline_event_id,
            timeMin=start,
            timeMax=end,
            maxResults=1,
        )
        .execute()
    )
    items = result.get("items", [])
    return items[0] if items else None


def override_baseline_occurrence(
    service,
    calendar_id: str,
    instance: dict,
    alarm_time: datetime,
    timezone_str: str,
    prep_minutes: int,
) -> dict:
    """Override a single occurrence of the baseline recurring event.

    Updates only the specific instance — future recurrences are not affected.
    """
    end_time = alarm_time + timedelta(minutes=prep_minutes)
    instance["start"] = {
        "dateTime": alarm_time.isoformat(),
        "timeZone": timezone_str,
    }
    instance["end"] = {
        "dateTime": end_time.isoformat(),
        "timeZone": timezone_str,
    }
    return (
        service.events()
        .update(calendarId=calendar_id, eventId=instance["id"], body=instance)
        .execute()
    )


def run_calendar_write(
    popup_response: dict,
    config: dict,
    meeting_name: str,
    prep_minutes: int,
) -> None:
    """Orchestrate the full calendar write flow.

    Does nothing if the popup was skipped or not confirmed.
    Otherwise: deletes existing alarm, writes new alarm, overrides baseline if present.

    Raises:
        Exception: re-raised with a human-readable message if any API call fails.
    """
    if popup_response.get("skipped") or not popup_response.get("confirmed"):
        return

    alarm_time: datetime = popup_response["alarm_time"]
    calendar_id: str = config["personal_calendar_id"]
    timezone_str: str = config.get("timezone", "America/New_York")
    baseline_event_id: str | None = config.get("baseline_event_id")

    service = get_calendar_service()

    # Delete existing system-written alarm events for tomorrow
    existing = get_existing_alarm_for_tomorrow(service, calendar_id, timezone_str)
    for event in existing:
        delete_alarm_event(service, calendar_id, event["id"])
        logger.info("Deleted existing alarm: %s", event.get("summary", "(no title)"))

    # Write the new alarm event
    try:
        written = write_alarm_event(
            service, calendar_id, alarm_time, meeting_name, timezone_str, prep_minutes
        )
        logger.info(
            "Alarm written: %s at %s (%d min)",
            written.get("summary"),
            alarm_time.strftime("%H:%M"),
            prep_minutes,
        )
    except Exception as exc:
        logger.error("Failed to write alarm event — %s", exc)
        raise

    # Override tomorrow's occurrence of the baseline recurring event if configured
    if baseline_event_id:
        instance = get_baseline_instance_for_tomorrow(
            service, calendar_id, baseline_event_id, timezone_str
        )
        if instance:
            try:
                override_baseline_occurrence(
                    service, calendar_id, instance, alarm_time, timezone_str, prep_minutes
                )
                print(
                    f"[calendar_writer] Baseline occurrence overridden: "
                    f"{instance.get('summary', '(no title)')} → {alarm_time.strftime('%H:%M')}"
                )
            except Exception as exc:
                print(f"[calendar_writer] ERROR: Failed to override baseline — {exc}")
                raise
        else:
            print("[calendar_writer] No baseline occurrence found for tomorrow; skipping override.")
