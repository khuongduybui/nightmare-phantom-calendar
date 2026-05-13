"""Nightly sync pipeline — orchestrates the full alarm computation and write flow."""

import subprocess
import sys
import threading
from datetime import datetime

import rumps

from calendar_reader import get_msi_time_blocks, get_personal_events
from calendar_writer import run_calendar_write
from compute import compute_alarm
from drive_config import append_recurring_meetings, parse_config, read_config

_SYNC_LOCK = threading.Lock()
_PENDING_RUN = threading.Event()


def _classify_unknown_blocks(
    unknown_blocks: list, config: dict, current_alarm: "datetime | None"
) -> "tuple[list, datetime | None]":
    """Show a classification dialog for each unknown MSI block.

    Returns (classifications, updated_alarm_time). Only integer-prep types are offered.
    Travel-time entries (e.g. 'travel+10') are excluded.
    """
    from datetime import timedelta

    meeting_type_prep = config.get("meeting_type_prep") or {}
    options = [
        (name, int(prep))
        for name, prep in meeting_type_prep.items()
        if isinstance(prep, int)
    ]
    if not options:
        return [], current_alarm

    option_names = [name for name, _ in options] + ["Skip (keep default)"]
    classifications = []
    alarm_time = current_alarm

    for block in sorted(unknown_blocks, key=lambda b: b["start"]):
        start_str = block["start"].strftime("%H:%M")
        items_str = ", ".join(f'"{n}"' for n in option_names)
        script = (
            f'tell application "System Events" to set sel to '
            f"choose from list {{{items_str}}} "
            f'with prompt "Unknown block at {start_str} — what type of meeting is this?" '
            f'default items {{"Skip (keep default)"}} '
            f'with title "Phantom Calendar"\n'
            f"if sel is false then\n"
            f'  return "__cancelled__"\n'
            f"else\n"
            f"  return item 1 of sel\n"
            f"end if"
        )
        out, _ = _osascript(script)
        selected = out.strip()
        if not selected or selected in ("__cancelled__", "Skip (keep default)"):
            continue
        prep_minutes = next((p for n, p in options if n == selected), None)
        if prep_minutes is None:
            continue
        candidate_alarm = block["start"] - timedelta(minutes=prep_minutes)
        if alarm_time is None or candidate_alarm < alarm_time:
            alarm_time = candidate_alarm
        classifications.append({
            "start_time": block["start"].isoformat(),
            "meeting_type": selected,
            "prep_minutes": prep_minutes,
        })

    return classifications, alarm_time


def _show_popup(result: dict, config: dict | None = None) -> dict:
    """Show the alarm confirmation dialog using osascript (works from any thread)."""
    meeting_name = result.get("first_meeting_name")

    # No meetings
    if meeting_name is None:
        _osascript(
            'tell application "System Events" to display dialog '
            '"No meetings found for tomorrow." buttons {"OK"} '
            'default button "OK" with title "Phantom Calendar"'
        )
        return {"confirmed": False, "alarm_time": None, "skipped": True, "classifications": []}

    alarm_time = result.get("alarm_time")
    prep = result.get("prep_minutes", 0)
    classifications: list = []

    # Classification dialogs for unknown blocks (normal mode only, not baseline)
    unknown = result.get("unknown_blocks") or []
    if unknown and config and not result.get("is_baseline"):
        classifications, alarm_time = _classify_unknown_blocks(unknown, config, alarm_time)

    alarm_str = alarm_time.strftime("%H:%M") if alarm_time else "—"

    # Build unknown block summary lines
    unknown_lines = ""
    for b in unknown:
        start = b["start"].strftime("%H:%M")
        matched = next(
            (c for c in classifications if c["start_time"] == b["start"].isoformat()), None
        )
        if matched:
            unknown_lines += f"\\n✅ {start} → {matched['meeting_type']} ({matched['prep_minutes']} min)"
        else:
            unknown_lines += f"\\n⚠️ Unknown block at {start} — default prep applied"

    # Baseline — no new event needed
    if result.get("is_baseline"):
        _osascript(
            f'tell application "System Events" to display dialog '
            f'"Meeting: {meeting_name}\\n'
            f'Alarm: {alarm_str} ({prep} min prep){unknown_lines}\\n\\n'
            f'✓ Matches baseline — no new event needed." '
            f'buttons {{"OK"}} default button "OK" with title "Phantom Calendar"'
        )
        return {"confirmed": False, "alarm_time": None, "skipped": False, "classifications": classifications}

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
        return {"confirmed": False, "alarm_time": None, "skipped": True, "classifications": classifications}

    time_str = out.split("||")[-1].strip() if "||" in out else alarm_str
    try:
        h, m = map(int, time_str.split(":"))
        confirmed_alarm = alarm_time.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        confirmed_alarm = alarm_time

    return {"confirmed": True, "alarm_time": confirmed_alarm, "skipped": False, "classifications": classifications}


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

        popup_response = _show_popup(result, config)

        run_calendar_write(
            popup_response,
            config,
            meeting_name=result["first_meeting_name"],
            prep_minutes=result["prep_minutes"],
        )

        # Write classifications back to Drive config (non-fatal)
        if popup_response.get("confirmed") and popup_response.get("classifications"):
            try:
                append_recurring_meetings(popup_response["classifications"], config)
                print(
                    f"[sync_job] Wrote {len(popup_response['classifications'])} "
                    "classification(s) to Drive config."
                )
            except Exception as exc:
                print(f"[sync_job] WARNING: Could not write classifications to Drive — {exc}", file=sys.stderr)

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
