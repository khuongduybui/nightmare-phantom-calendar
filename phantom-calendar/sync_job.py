"""Nightly sync pipeline — orchestrates the full alarm computation and write flow."""

import sys
import threading

import rumps

from calendar_reader import get_msi_time_blocks, get_personal_events
from calendar_writer import run_calendar_write
from compute import compute_alarm
from drive_config import parse_config, read_config
from popup import ConfirmationPopup

_SYNC_LOCK = threading.Lock()


def run_nightly_sync(app_ref=None) -> None:
    """Run the full nightly sync pipeline.

    Args:
        app_ref: Optional PhantomCalendarApp instance. If provided, its
            set_syncing() and update_sync_state() methods are called to
            update the menu bar icon and status items.

    Execution order:
        read_config → parse_config → get_msi_time_blocks → get_personal_events
        → compute_alarm → ConfirmationPopup.show() → run_calendar_write()

    Protected by a module-level lock — returns immediately without running
    if a sync is already in progress (prevents double-trigger).

    On any pipeline error: surfaces via rumps.notification + stderr, does not re-raise.
    """
    if not _SYNC_LOCK.acquire(blocking=False):
        print("[sync_job] Sync already in progress — skipping.", file=sys.stderr)
        return

    if app_ref is not None:
        try:
            app_ref.set_syncing(True)
        except Exception:
            pass

    alarm_time = None
    failed = False

    try:
        raw = read_config()
        config = parse_config(raw)

        timezone_str = config.get("timezone", "America/New_York")
        msi_blocks = get_msi_time_blocks()
        personal_events = get_personal_events()

        result = compute_alarm(msi_blocks, personal_events, config)
        alarm_time = result.get("alarm_time")

        popup_response = ConfirmationPopup(result).show()

        run_calendar_write(
            popup_response,
            config,
            meeting_name=result["first_meeting_name"],
            prep_minutes=result["prep_minutes"],
        )

    except Exception as exc:
        failed = True
        msg = str(exc)
        print(f"[sync_job] ERROR: {msg}", file=sys.stderr)
        try:
            rumps.notification("Phantom Calendar", "", msg)
        except Exception:
            pass  # notification failure must never mask the original error log

    finally:
        _SYNC_LOCK.release()
        if app_ref is not None:
            try:
                app_ref.update_sync_state(alarm_time, failed)
            except Exception:
                pass
