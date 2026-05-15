"""Compute module — matches MSI blocks to meetings and computes alarm time."""

from datetime import datetime, timedelta


def _parse_fixed_minutes(val) -> int:
    """Parse a prep value: int → itself, 'travel+N' → N, else 0."""
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.startswith("travel+"):
        try:
            return int(val.split("+", 1)[1])
        except (ValueError, IndexError):
            pass
    return 0


def resolve_prep_minutes(
    meeting: dict,
    config: dict,
    event_location: "str | None" = None,
) -> int:
    """Resolve prep minutes for a meeting, applying travel time if applicable.

    Args:
        meeting: A meeting/event dict (recurring meeting entry or personal event).
        config: Parsed config dict with 'locations', 'meeting_type_prep', etc.
        event_location: Location string from the calendar API (personal events only).
            Empty string → "Home". None → use meeting["location"] field.

    Returns:
        Total prep minutes (travel + fixed overhead).
    """
    locations = config.get("locations") or {}

    # Determine location name
    if event_location is not None:
        location_name = event_location.strip() or "Home"
    else:
        location_name = meeting.get("location") or None

    if location_name:
        travel_minutes = locations.get(location_name, locations.get("Home", 0))
        meeting_type = meeting.get("meeting_type")
        if meeting_type:
            type_val = config.get("meeting_type_prep", {}).get(
                meeting_type, meeting.get("prep_minutes", 0)
            )
        else:
            type_val = meeting.get("prep_minutes", 0)
        fixed = _parse_fixed_minutes(type_val)
        return int(travel_minutes) + fixed
    else:
        return meeting.get("prep_minutes", config.get("default_prep_minutes", 30))


def match_block_to_meeting(block: dict, recurring_meetings: list) -> dict | None:
    """Match an MSI time block to a known recurring meeting by start time.

    Match tolerance: within 5 minutes (300 seconds).
    Returns the matched meeting dict or None.
    """
    block_start: datetime = block["start"]
    for meeting in recurring_meetings:
        try:
            meeting_time = datetime.strptime(meeting["start"], "%H:%M")
        except (ValueError, KeyError):
            continue

        meeting_start = block_start.replace(
            hour=meeting_time.hour,
            minute=meeting_time.minute,
            second=0,
            microsecond=0,
        )
        delta = abs((block_start - meeting_start).total_seconds())
        if delta <= 300:
            return meeting

    return None


def compute_alarm(
    msi_blocks: list,
    personal_events: list,
    config: dict,
) -> dict:
    """Compute the alarm time for tomorrow's first meeting.

    Returns a dict with exactly 7 keys:
    - first_meeting_name: str | None
    - first_meeting_time: datetime | None
    - prep_minutes: int
    - alarm_time: datetime | None
    - is_baseline: bool
    - all_meetings: list
    - unknown_blocks: list
    """
    recurring_meetings = config.get("recurring_meetings", [])
    default_prep = config.get("default_prep_minutes", 30)
    baseline_title = config.get("baseline_event_title", "")
    baseline_time_str = config.get("baseline_event_time", "")

    candidates = []
    unknown_blocks = []

    # Process MSI blocks
    for block in msi_blocks:
        matched = match_block_to_meeting(block, recurring_meetings)
        if matched:
            prep = resolve_prep_minutes(matched, config)
            candidates.append({
                "name": matched["name"],
                "time": block["start"],
                "prep_minutes": prep,
                "source": "msi_known",
            })
        else:
            unknown_blocks.append(block)
            candidates.append({
                "name": "Unknown MSI meeting",
                "time": block["start"],
                "prep_minutes": default_prep,
                "source": "msi_unknown",
            })

    # Process personal events — exclude alarm events
    for event in personal_events:
        if "Alarm" in event.get("title", ""):
            continue
        event_loc = event.get("location")  # may be None or a string
        prep = resolve_prep_minutes(event, config, event_location=event_loc)
        candidates.append({
            "name": event["title"],
            "time": event["start"],
            "prep_minutes": prep,
            "source": "personal",
        })

    if not candidates:
        return {
            "first_meeting_name": None,
            "first_meeting_time": None,
            "prep_minutes": 0,
            "alarm_time": None,
            "is_baseline": True,
            "all_meetings": [],
            "unknown_blocks": unknown_blocks,
        }

    # Sort by time and pick the earliest
    candidates.sort(key=lambda x: x["time"])
    first = candidates[0]
    alarm_time = first["time"] - timedelta(minutes=first["prep_minutes"])

    # Check if alarm matches the baseline
    is_baseline = _is_baseline_alarm(
        first["name"], alarm_time, baseline_title, baseline_time_str
    )

    return {
        "first_meeting_name": first["name"],
        "first_meeting_time": first["time"],
        "prep_minutes": first["prep_minutes"],
        "alarm_time": alarm_time,
        "is_baseline": is_baseline,
        "all_meetings": candidates,
        "unknown_blocks": unknown_blocks,
    }


def _is_baseline_alarm(
    meeting_name: str,
    alarm_time: datetime,
    baseline_title: str,
    baseline_time_str: str,
) -> bool:
    """Return True if alarm matches the configured baseline event."""
    if not baseline_title or meeting_name != baseline_title:
        return False
    if not baseline_time_str:
        return False
    try:
        bt = datetime.strptime(baseline_time_str, "%H:%M")
        return alarm_time.hour == bt.hour and alarm_time.minute == bt.minute
    except ValueError:
        return False
