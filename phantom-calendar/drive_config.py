"""Drive config — reads, bootstraps, and parses YAML config from Google Drive."""

import io
import os

import yaml

from auth import get_drive_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE_ID = os.environ.get(
    "PHANTOM_CONFIG_FILE_ID", "1nZ8-G5vwi9O8r4hAmbBS9zl55cVVjXz6"
)

# Default config — mirrors config.yaml at the project root.
with open(os.path.join(BASE_DIR, "config.yaml"), "r") as _f:
    DEFAULT_CONFIG_YAML = _f.read()

_DEFAULTS = {
    "personal_calendar_id": "duykbui1989@gmail.com",
    "msi_calendar_id": "duy.bui@motorolasolutions.com",
    "daily_run_time": "19:00",
    "timezone": "America/New_York",
    "default_prep_minutes": 30,
    "baseline_event_id": "l13abvd0p0vkphit24u6bkhuf8",
    "baseline_event_title": "Daily Standup Alarm",
    "baseline_event_time": "09:25",
    "recurring_meetings": [],
    "meeting_type_prep": {},
    "locations": {},
    "client_overrides": {},
}


def read_config() -> str:
    """Fetch config from Drive. Bootstraps with defaults if content is invalid YAML."""
    service = get_drive_service()
    request = service.files().get_media(fileId=CONFIG_FILE_ID)
    raw = request.execute()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    # Validate YAML — bootstrap if invalid or empty
    try:
        parsed = yaml.safe_load(raw)
        if not parsed:
            raise ValueError("empty")
    except Exception:
        bootstrap_config()
        return DEFAULT_CONFIG_YAML

    return raw


def bootstrap_config() -> None:
    """Write DEFAULT_CONFIG_YAML to Drive and rename the file to config.yaml if needed."""
    write_config(DEFAULT_CONFIG_YAML)

    service = get_drive_service()
    meta = service.files().get(fileId=CONFIG_FILE_ID, fields="name").execute()
    current_name = meta.get("name", "")
    if not current_name.endswith(".yaml"):
        service.files().update(
            fileId=CONFIG_FILE_ID,
            body={"name": "config.yaml"},
        ).execute()


def write_config(content: str) -> None:
    """Upload content string to the Drive config file."""
    service = get_drive_service()
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")), mimetype="text/plain"
    )
    service.files().update(
        fileId=CONFIG_FILE_ID,
        media_body=media,
    ).execute()


def parse_config(raw: str) -> dict:
    """Parse YAML config string into a structured dict with sane defaults."""
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        data = {}

    calendars = data.get("calendars") or {}
    baseline = data.get("baseline_event") or {}

    # Normalise recurring meetings — ensure 'notes' key always present
    raw_meetings = data.get("recurring_meetings") or []
    meetings = []
    for m in raw_meetings:
        if not isinstance(m, dict):
            continue
        meetings.append(
            {
                "name": m.get("name", ""),
                "start": m.get("start", ""),
                "end": m.get("end", ""),
                "days": m.get("days") or [],
                "prep_minutes": int(
                    m.get("prep_minutes", _DEFAULTS["default_prep_minutes"])
                ),
                "notes": m.get("notes", ""),
            }
        )

    return {
        "personal_calendar_id": calendars.get(
            "personal_id", _DEFAULTS["personal_calendar_id"]
        ),
        "msi_calendar_id": calendars.get("msi_id", _DEFAULTS["msi_calendar_id"]),
        "daily_run_time": calendars.get("daily_run_time", _DEFAULTS["daily_run_time"]),
        "timezone": data.get("timezone", _DEFAULTS["timezone"]),
        "default_prep_minutes": int(
            data.get("default_prep_minutes", _DEFAULTS["default_prep_minutes"])
        ),
        "baseline_event_id": baseline.get("id", _DEFAULTS["baseline_event_id"]),
        "baseline_event_title": baseline.get(
            "title", _DEFAULTS["baseline_event_title"]
        ),
        "baseline_event_time": baseline.get("time", _DEFAULTS["baseline_event_time"]),
        "recurring_meetings": meetings,
        "meeting_type_prep": data.get("meeting_type_prep") or {},
        "locations": data.get("locations") or {},
        "client_overrides": data.get("client_overrides") or {},
    }
