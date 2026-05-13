"""Nightly sync pipeline — orchestrates the full alarm computation and write flow."""

import subprocess
import sys
import threading
from datetime import datetime

import rumps

from calendar_reader import get_msi_time_blocks, get_personal_events
from calendar_writer import run_calendar_write
from compute import compute_alarm
from drive_config import parse_config, read_config

_SYNC_LOCK = threading.Lock()
_PENDING_RUN = threading.Event()


def _show_popup(result: dict) -> dict:
    """Show the alarm confirmation dialog using osascript (works from any thread).

    Using tkinter (popup.py) crashes when called from a background thread inside
    a rumps app because AppKit owns the main thread. osascript spawns a subprocess
    and shows a native macOS dialog safely from any thread.
    """
    meeting_name = result.get("first_meeting_name")

    # No meetings
    if meeting_name is None:
        _osascript(
            'tell application "System Events" to display dialog '
            '"No meetings found for tomorrow." buttons {"OK"} '
            'default button "OK" with title "Phantom Calendar"'
        )
        return {"confirmed": False, "alarm_time": None, "skipped": True}

    alarm_time = result.get("alarm_time")
    alarm_str = alarm_time.strftime("%H:%M") if alarm_time else "—"
    prep = result.get("prep_minutes", 0)

    unknown = result.get("unknown_blocks") or []
    unknown_lines = "".join(
        f"\\n⚠️ Unknown block at {b['start'].strftime('%H:%M')} — default prep applied"
        for b in unknown
    )

    # Baseline — no new event needed
    if result.get("is_baseline"):
        _osascript(
            f'tell application "System Events" to display dialog '
            f'"Meeting: {meeting_name}\\n'
            f'Alarm: {alarm_str} ({prep} min prep){unknown_lines}\\n\\n'
            f'✓ Matches baseline — no new event needed." '
            f'buttons {{"OK"}} default button "OK" with title "Phantom Calendar"'
        )
        return {"confirmed": False, "alarm_time": None, "skipped": False}

    # Normal mode — ask to confirm/edit alarm time
    script = (
        f'tell application "System Events"\\n'
        f'  set r to display dialog '
        f'"Meeting: {meeting_name}\\n'
        f'Meeting time: {result["first_meeting_time"].strftime("%H:%M")}\\n'
        f'Prep: {prep} min{unknown_lines}\\n\\n'
        f'Alarm time (HH:MM):" '
        f'default answer "{alarm_str}" '
        f'buttons {{"Skip", "Write to Calendar"}} '
        f'default button "Write to Calendar" '
        f'with title "Phantom Calendar"\\n'
        f'  return (button returned of r) & "||" & (text returned of r)\\n'
        f'end tell'
    )
    out, rc = _osascript(script)

    if rc != 0 or "Write to Calendar" not in out:
        return {"confirmed": False, "alarm_time": None, "skipped": True}

    time_str = out.split("||")[-1].strip() if "||" in out else alarm_str
    try:
        h, m = map(int, time_str.split(":"))
        confirmed_alarm = alarm_time.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        confirmed_alarm = alarm_time

    return {"confirmed": True, "alarm_time": confirmed_alarm, "skipped": False}


def _osascript(script: str) -> tuple[str, int]:
    """Run an AppleScript snippet. Returns (stdout, returncode)."""
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,  # 5 min — user has time to respond
    )
    return proc.stdout.strip(), proc.returncode


def queue_run(app_ref=None) -> None:
    """Request a sync run, queuing it if one is already in progress.

    If no sync is running, calls run_nightly_sync() directly.
    If a sync is running, sets _PENDING_RUN so the current run triggers
    a follow-up immediately after it completes (at most one pending run).
    """
    if _SYNC_LOCK.locked():
        _PENDING_RUN.set()
        print("[sync_job] Sync in progress — queued one pending run.", file=sys.stderr)
    else:
        run_nightly_sync(app_ref)


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

        popup_response = _show_popup(result)

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
        # Run any queued on-demand sync now that the lock is free
        if _PENDING_RUN.is_set():
            _PENDING_RUN.clear()
            run_nightly_sync(app_ref)
