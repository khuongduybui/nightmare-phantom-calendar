"""Drive config — reads, bootstraps, and parses YAML config from Google Drive."""

import io
import os

import yaml

from auth import get_drive_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Local config.yaml path — used as default/fallback and kept in sync with Drive.
CONFIG_YAML_PATH = os.path.join(BASE_DIR, "config.yaml")

# Local file that persists the Drive config file ID across restarts.
DRIVE_CONFIG_ID_FILE = os.path.join(BASE_DIR, ".drive_config_id")


def _load_config_file_id() -> str:
    """Return the Drive config file ID, preferring (in order):
    1. PHANTOM_CONFIG_FILE_ID env var
    2. Contents of .drive_config_id local file
    3. Hardcoded default (may no longer exist on Drive)
    """
    if env_id := os.environ.get("PHANTOM_CONFIG_FILE_ID"):
        return env_id
    if os.path.exists(DRIVE_CONFIG_ID_FILE):
        with open(DRIVE_CONFIG_ID_FILE) as f:
            stored = f.read().strip()
            if stored:
                return stored
    return "1nPSl33iRhs5Jnv1SxNxdc9qHoID5J1UF"


def _save_config_file_id(file_id: str) -> None:
    """Persist a Drive file ID to the local .drive_config_id file."""
    with open(DRIVE_CONFIG_ID_FILE, "w") as f:
        f.write(file_id)


CONFIG_FILE_ID = _load_config_file_id()

# When True, read_config() returns the local config.yaml instead of fetching from Drive.
_use_local_config: bool = False


def set_local_config_mode(enabled: bool) -> None:
    """Enable or disable local-config override mode.

    When enabled, read_config() reads config.yaml from disk instead of Drive.
    write_config() always mirrors to disk regardless of this flag.
    """
    global _use_local_config
    _use_local_config = enabled


# Default config — mirrors config.yaml at the project root.
with open(CONFIG_YAML_PATH, "r") as _f:
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
    "apple_exclude_calendars": [],
}


def read_config() -> str:
    """Fetch config from Drive. Creates a new file if not found (404).
    Bootstraps with defaults if content is invalid YAML.

    When local-config mode is active (--local-config flag), reads config.yaml
    from disk instead of Drive.
    """
    if _use_local_config:
        print("[drive_config] Local-config mode: reading config.yaml from disk.")
        with open(CONFIG_YAML_PATH) as f:
            return f.read()

    global CONFIG_FILE_ID
    service = get_drive_service()

    try:
        request = service.files().get_media(fileId=CONFIG_FILE_ID)
        raw = request.execute()
    except Exception as exc:
        # 404 or any other error — create a fresh config file on Drive
        print(f"[drive_config] Config file not found ({exc}); creating new file on Drive.")
        new_id = _create_config_file(service)
        CONFIG_FILE_ID = new_id
        _save_config_file_id(new_id)
        print(f"[drive_config] Created new Drive config file: {new_id}")
        return DEFAULT_CONFIG_YAML

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


def _create_config_file(service) -> str:
    """Create a new plain-text config file on Drive with DEFAULT_CONFIG_YAML content.

    Returns the new file's Drive ID.
    """
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(DEFAULT_CONFIG_YAML.encode("utf-8")), mimetype="text/plain"
    )
    file_meta = {"name": "config.yaml"}
    created = (
        service.files()
        .create(body=file_meta, media_body=media, fields="id")
        .execute()
    )
    return created["id"]


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
    """Upload content string to the Drive config file and mirror to local config.yaml."""
    service = get_drive_service()
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")), mimetype="text/plain"
    )
    service.files().update(
        fileId=CONFIG_FILE_ID,
        media_body=media,
    ).execute()

    # Mirror to local file so config.yaml stays in sync with Drive.
    try:
        with open(CONFIG_YAML_PATH, "w") as f:
            f.write(content)
    except Exception as exc:
        print(f"[drive_config] WARNING: Could not mirror config to local file — {exc}")


def append_recurring_meetings(classifications: list, config: dict) -> None:
    """Append classified unknown blocks to recurring_meetings in the Drive config.

    Each classification dict must have: start_time (ISO str), meeting_type (str),
    prep_minutes (int). Builds a new recurring meeting entry and writes back to Drive.
    """
    from datetime import datetime, timedelta

    existing_meetings = list(config.get("recurring_meetings") or [])

    for c in classifications:
        try:
            start_dt = datetime.fromisoformat(c["start_time"])
        except (ValueError, KeyError):
            continue
        start_str = start_dt.strftime("%H:%M")
        end_dt = start_dt + timedelta(minutes=c["prep_minutes"])
        end_str = end_dt.strftime("%H:%M")
        meeting_type = c["meeting_type"]
        prep = c["prep_minutes"]

        new_entry = {
            "name": f"{meeting_type} ({start_str})",
            "start": start_str,
            "end": end_str,
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "prep_minutes": prep,
            "meeting_type": meeting_type,
            "notes": "Auto-classified by Phantom Calendar",
        }
        if c.get("location"):
            new_entry["location"] = c["location"]
        existing_meetings.append(new_entry)

    # Build updated config dict and serialize back to YAML
    updated_data = {
        "calendars": {
            "personal_id": config["personal_calendar_id"],
            "msi_id": config["msi_calendar_id"],
            "daily_run_time": config.get("daily_run_time", "21:00"),
        },
        "timezone": config.get("timezone", "America/New_York"),
        "default_prep_minutes": config.get("default_prep_minutes", 30),
        "baseline_event": {
            "id": config.get("baseline_event_id", ""),
            "title": config.get("baseline_event_title", ""),
            "time": config.get("baseline_event_time", "09:25"),
        },
        "recurring_meetings": existing_meetings,
        "meeting_type_prep": config.get("meeting_type_prep") or {},
        "locations": config.get("locations") or {},
        "client_overrides": config.get("client_overrides") or {},
    }
    write_config(yaml.dump(updated_data, default_flow_style=False, allow_unicode=True))


def append_locations(location_travel_minutes: dict, config: dict) -> None:
    """Merge new location → travel-minutes mappings into the Drive config.

    Existing locations are not overwritten. New entries are merged on top of
    existing ones, then the full config is written back to Drive.
    """
    existing_locations = config.get("locations") or {}
    # Existing entries take precedence — new entries only added where not present
    updated_locations = {**location_travel_minutes, **existing_locations}

    updated_data = {
        "calendars": {
            "personal_id": config["personal_calendar_id"],
            "msi_id": config["msi_calendar_id"],
            "daily_run_time": config.get("daily_run_time", "21:00"),
        },
        "timezone": config.get("timezone", "America/New_York"),
        "default_prep_minutes": config.get("default_prep_minutes", 30),
        "baseline_event": {
            "id": config.get("baseline_event_id", ""),
            "title": config.get("baseline_event_title", ""),
            "time": config.get("baseline_event_time", "09:25"),
        },
        "recurring_meetings": list(config.get("recurring_meetings") or []),
        "meeting_type_prep": config.get("meeting_type_prep") or {},
        "locations": updated_locations,
        "client_overrides": config.get("client_overrides") or {},
    }
    write_config(yaml.dump(updated_data, default_flow_style=False, allow_unicode=True))


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
        entry = {
                "name": m.get("name", ""),
                "start": m.get("start", ""),
                "end": m.get("end", ""),
                "days": m.get("days") or [],
                "prep_minutes": int(
                    m.get("prep_minutes", _DEFAULTS["default_prep_minutes"])
                ),
                "notes": m.get("notes", ""),
            }
        # Pass through optional location/meeting_type fields
        if m.get("location"):
            entry["location"] = m["location"]
        if m.get("meeting_type"):
            entry["meeting_type"] = m["meeting_type"]
        meetings.append(entry)

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
        "locations": _ensure_home_location(data.get("locations") or {}),
        "client_overrides": data.get("client_overrides") or {},
        "apple_exclude_calendars": _parse_apple_exclude(calendars),
    }


def _parse_apple_exclude(calendars: dict) -> list[str]:
    """Extract apple_exclude_calendars from the calendars config section."""
    raw = calendars.get("apple_exclude_calendars")
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []


def _ensure_home_location(locations: dict) -> dict:
    """Inject 'Home': 0 into the locations dict if not already present."""
    if "Home" not in locations:
        locations = dict(locations)
        locations["Home"] = 0
    return locations
