"""Nightly sync pipeline — orchestrates the full alarm computation and write flow."""

import os
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta

import rumps

import apple_calendar
import osaurus_client
from calendar_reader import get_msi_time_blocks, get_personal_events
from calendar_writer import run_calendar_write
from compute import compute_alarm, match_block_to_meeting
from drive_config import append_locations, append_recurring_meetings, parse_config, read_config

_SYNC_LOCK = threading.Lock()
_PENDING_RUN = threading.Event()

# Set PHANTOM_APPLE_DEBUG=1 to enable verbose debug logging across the sync pipeline.
_DEBUG = os.environ.get("PHANTOM_APPLE_DEBUG", "") == "1"


def _dbg(msg: str) -> None:
    """Print a debug line to stderr when PHANTOM_APPLE_DEBUG=1."""
    if _DEBUG:
        print(f"[sync_job] {msg}", file=sys.stderr)


def _ask_recurring_or_oneshot() -> bool:
    """Ask whether to save the classification for future runs.

    Returns True for Recurring, False for One-shot or cancellation.
    """
    script = (
        'tell application "System Events" to set r to display dialog '
        '"Save this for future runs?" '
        'buttons {"One-shot", "Recurring"} default button "Recurring" '
        'with title "Phantom Calendar"\n'
        'if button returned of r is "Recurring" then return "Recurring"\n'
        'return "One-shot"'
    )
    out, rc = _osascript(script)
    return rc == 0 and out.strip() == "Recurring"


def _classify_unknown_blocks(
    unknown_blocks: list, config: dict, current_alarm: "datetime | None"
) -> "tuple[list, datetime | None]":
    """Show a classification dialog for each unknown MSI block.

    Returns (classifications, updated_alarm_time). Only integer-prep types are offered.
    Travel-time entries (e.g. 'travel+10') are excluded.
    Recurring classifications are appended to the returned list; One-shot
    classifications update the alarm time only.
    """
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

        # Get AI suggestion (belt-and-suspenders: client already catches all exceptions)
        _osaurus_title = block.get("title", "Untitled")
        _osaurus_desc = block.get("description", "")
        _dbg(f"osaurus query (MSI): title={_osaurus_title!r} description={_osaurus_desc[:80]!r}")
        try:
            suggestion = osaurus_client.suggest_meeting_type(
                _osaurus_title,
                _osaurus_desc,
                [name for name, _ in options],
            )
        except Exception as _osa_exc:
            _dbg(f"osaurus error (MSI): {_osa_exc}")
            suggestion = None
        _dbg(f"osaurus suggestion (MSI): {suggestion!r}")

        title_str = block.get("title", "").replace('"', "'") or "Untitled"
        default_item = suggestion if suggestion else "Skip (keep default)"
        items_str = ", ".join(f'"{n}"' for n in option_names)
        script = (
            f'tell application "System Events" to set sel to '
            f"choose from list {{{items_str}}} "
            f'with prompt "{title_str} at {start_str} — what type of meeting is this?" '
            f'default items {{"{default_item}"}} '
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

        # Ask for meeting location
        location = _ask_location(config)

        # Recalculate alarm using travel time if location provided
        from compute import resolve_prep_minutes
        dummy_meeting = {"prep_minutes": prep_minutes, "meeting_type": selected}
        resolved = resolve_prep_minutes(dummy_meeting, config, event_location=location or "")
        candidate_alarm = block["start"] - timedelta(minutes=resolved)
        if alarm_time is None or candidate_alarm < alarm_time:
            alarm_time = candidate_alarm

        # Ask whether to save for future runs
        recurring = _ask_recurring_or_oneshot()
        if recurring:
            entry = {
                "start_time": block["start"].isoformat(),
                "meeting_type": selected,
                "prep_minutes": resolved,
            }
            if location:
                entry["location"] = location
            classifications.append(entry)

    return classifications, alarm_time


def _ask_location(config: dict) -> str:
    """Ask user where the unknown meeting is via osascript. Returns location name or ''."""
    locations = config.get("locations") or {}
    loc_names = [name for name in locations if name != "Home"]
    choices = loc_names + ["Home (no extra travel)", "Somewhere else…", "Skip"]
    items_str = ", ".join(f'"{n}"' for n in choices)
    script = (
        f'tell application "System Events" to set sel to '
        f"choose from list {{{items_str}}} "
        f'with prompt "Where is this meeting?" '
        f'default items {{"Skip"}} '
        f'with title "Phantom Calendar"\n'
        f"if sel is false then\n  return \"Skip\"\n"
        f"else\n  return item 1 of sel\nend if"
    )
    out, _ = _osascript(script)
    selected = out.strip()
    if not selected or selected == "Skip":
        return ""
    if selected == "Home (no extra travel)":
        return "Home"
    if selected == "Somewhere else…":
        name_script = (
            'tell application "System Events" to set r to display dialog '
            '"Enter location name:" default answer "" '
            'buttons {"Cancel", "OK"} default button "OK" '
            'with title "Phantom Calendar"\n'
            'if button returned of r is "Cancel" then return ""\n'
            'return text returned of r'
        )
        name_out, name_rc = _osascript(name_script)
        return name_out.strip() if name_rc == 0 else ""
    return selected


def _prompt_unknown_locations(
    unknown_locs: list, config: dict, current_alarm: "datetime | None"
) -> "tuple[dict, datetime | None]":
    """Show one osascript dialog per unique location in unknown_locs.

    Groups events that share the same location string. Prompts for an integer
    travel-minutes value (default "0"). Recalculates alarm_time when the
    entered value is non-zero and the event is earlier than the current alarm.

    Returns:
        (location_travel_minutes, updated_alarm_time) where location_travel_minutes
        contains only entries with non-zero integer values.
    """
    from datetime import timedelta

    # Group by location string
    groups: dict[str, list] = {}
    for entry in unknown_locs:
        loc = entry["location"]
        groups.setdefault(loc, []).append(entry)

    location_travel_minutes: dict = {}
    alarm_time = current_alarm

    for location, entries in groups.items():
        safe_location = location.replace('"', "'")
        safe_titles = ", ".join(e["title"].replace('"', "'") for e in entries)
        prompt_text = (
            f"Location: {safe_location}\\n"
            f"Event(s): {safe_titles}\\n\\n"
            "How many minutes of travel time?"
        )
        script = (
            f'tell application "System Events" to set r to display dialog '
            f'"{prompt_text}" '
            f'default answer "0" '
            f'buttons {{"Skip", "OK"}} default button "OK" '
            f'with title "Phantom Calendar"\n'
            f'if button returned of r is "Skip" then return ""\n'
            f'return text returned of r'
        )
        out, rc = _osascript(script)
        raw_val = out.strip()

        # Cancellation (rc != 0) or blank/non-integer → treat as 0, skip entry
        if rc != 0 or not raw_val:
            continue
        try:
            travel_minutes = int(raw_val)
        except ValueError:
            continue
        if travel_minutes <= 0:
            continue

        location_travel_minutes[location] = travel_minutes

        # Recalculate alarm: check each event in this location group
        for entry in entries:
            try:
                from datetime import datetime as _dt
                event_start = _dt.fromisoformat(entry["start_time"])
            except (ValueError, KeyError):
                continue
            candidate_alarm = event_start - timedelta(minutes=travel_minutes)
            if alarm_time is None or candidate_alarm < alarm_time:
                alarm_time = candidate_alarm

    return location_travel_minutes, alarm_time


def _classify_personal_events(
    personal_events: list, config: dict, current_alarm: "datetime | None"
) -> "tuple[list, datetime | None]":
    """Show a classification dialog for each personal calendar event.

    Mirrors the MSI block classification flow: ask osaurus for a suggestion,
    show a choose-from-list dialog, then ask Recurring vs One-shot.
    Returns (classifications_delta, updated_alarm_time).
    Recurring classifications are appended to the returned list; One-shot
    updates the alarm time only.
    """
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

    recurring_meetings = config.get("recurring_meetings") or []

    for event in personal_events:
        title = event.get("title", "Untitled")
        description = event.get("description", "")
        start = event.get("start")
        if start is None:
            continue

        # Skip events already matched to a recurring_meetings entry
        if match_block_to_meeting({"start": start}, recurring_meetings):
            continue

        # Get AI suggestion
        _dbg(f"osaurus query (personal): title={title!r} description={description[:80]!r}")
        try:
            suggestion = osaurus_client.suggest_meeting_type(
                title,
                description,
                [name for name, _ in options],
            )
        except Exception as _osa_exc:
            _dbg(f"osaurus error (personal): {_osa_exc}")
            suggestion = None
        _dbg(f"osaurus suggestion (personal): {suggestion!r}")

        default_item = suggestion if suggestion else "Skip (keep default)"
        safe_title = title.replace('"', "'")
        items_str = ", ".join(f'"{n}"' for n in option_names)
        start_str = start.strftime("%H:%M")
        script = (
            f'tell application "System Events" to set sel to '
            f"choose from list {{{items_str}}} "
            f'with prompt "Personal event at {start_str}: {safe_title}\\nWhat type of meeting is this?" '
            f'default items {{"{default_item}"}} '
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

        candidate_alarm = start - timedelta(minutes=prep_minutes)
        if alarm_time is None or candidate_alarm < alarm_time:
            alarm_time = candidate_alarm

        # Ask whether to save for future runs
        recurring = _ask_recurring_or_oneshot()
        if recurring:
            classifications.append({
                "start_time": start.isoformat(),
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
        return {"confirmed": False, "alarm_time": None, "skipped": True, "classifications": [], "location_travel_minutes": {}}

    alarm_time = result.get("alarm_time")
    prep = result.get("prep_minutes", 0)
    classifications: list = []
    location_travel_minutes: dict = {}

    # Classification dialogs for unknown blocks (normal mode only, not baseline)
    unknown = result.get("unknown_blocks") or []
    if unknown and config and not result.get("is_baseline"):
        classifications, alarm_time = _classify_unknown_blocks(unknown, config, alarm_time)

    # Prompt for unknown personal event locations (normal mode only, not baseline)
    unknown_locs = result.get("unknown_personal_locations") or []
    if unknown_locs and config and not result.get("is_baseline"):
        location_travel_minutes, alarm_time = _prompt_unknown_locations(
            unknown_locs, config, alarm_time
        )

    # Personal event type classification (normal mode only, not baseline)
    personal_events = result.get("personal_events") or []
    if personal_events and config and not result.get("is_baseline"):
        personal_classifications, alarm_time = _classify_personal_events(
            personal_events, config, alarm_time
        )
        classifications.extend(personal_classifications)

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
        return {"confirmed": False, "alarm_time": None, "skipped": False, "classifications": classifications, "location_travel_minutes": location_travel_minutes}

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
        return {"confirmed": False, "alarm_time": None, "skipped": True, "classifications": classifications, "location_travel_minutes": location_travel_minutes}

    time_str = out.split("||")[-1].strip() if "||" in out else alarm_str
    try:
        h, m = map(int, time_str.split(":"))
        confirmed_alarm = alarm_time.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        confirmed_alarm = alarm_time

    return {"confirmed": True, "alarm_time": confirmed_alarm, "skipped": False, "classifications": classifications, "location_travel_minutes": location_travel_minutes}


def _osascript(script: str) -> tuple[str, int]:
    """Run an AppleScript snippet. Returns (stdout, returncode)."""
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,  # 5 min — user has time to respond
    )
    return proc.stdout.strip(), proc.returncode


def queue_run(app_ref=None, target_date=None) -> None:
    """Request a sync run, queuing it if one is already in progress.

    If no sync is running, calls run_nightly_sync() directly.
    If a sync is running, sets _PENDING_RUN so the current run triggers
    a follow-up immediately after it completes (at most one pending run).
    Note: target_date is NOT queued — it only applies to direct immediate runs.
    """
    if _SYNC_LOCK.locked():
        _PENDING_RUN.set()
        print("[sync_job] Sync in progress — queued one pending run.", file=sys.stderr)
    else:
        run_nightly_sync(app_ref, target_date=target_date)


def run_nightly_sync(app_ref=None, target_date=None) -> None:
    """Run the full nightly sync pipeline.

    Args:
        app_ref: Optional PhantomCalendarApp instance. If provided, its
            set_syncing() and update_sync_state() methods are called to
            update the menu bar icon and status items.

    Execution order:
        read_config → parse_config → [Apple Calendar reads | Google Calendar reads]
        → compute_alarm → ConfirmationPopup.show() → run_calendar_write()

    Read source selection (per-run, automatic):
        If apple_calendar.is_accessible() returns True, events are read from all
        Apple Calendars via ical-guy and merged into a unified pool (passed as
        msi_blocks to compute_alarm with personal_events=[]). On any failure,
        falls back to Google Calendar reads with a rumps.notification.
        If apple_calendar.is_accessible() returns False, Google Calendar reads
        are used silently (pre-NPC-0014 behavior).

    The alarm write path (run_calendar_write) always targets Google Calendar.

    Protected by a module-level lock — returns immediately without running
    if a sync is already in progress (prevents double-trigger).

    On any pipeline error: surfaces via rumps.notification + stderr, does not re-raise.
    """
    if not _SYNC_LOCK.acquire(blocking=False):
        print("[sync_job] Sync already in progress — skipping.", file=sys.stderr)
        return

    debug = target_date is not None

    if debug:
        print(f"[DEBUG] === Phantom Calendar — debug/triage mode for {target_date} ===")

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
        if debug:
            print(f"[DEBUG] Timezone: {timezone_str}")

        use_apple = apple_calendar.is_accessible()
        if debug:
            print(f"[DEBUG] Read source: {'Apple Calendar' if use_apple else 'Google Calendar'}")

        if use_apple:
            try:
                _target = target_date if target_date is not None else date.today() + timedelta(days=1)
                unified = apple_calendar.get_tomorrow_events(
                    _target,
                    config.get("apple_exclude_calendars", []),
                )
                # Filter out alarm events that may have synced from Google into Calendar.app
                unified = [e for e in unified if "Alarm" not in e.get("title", "")]
                msi_blocks = unified
                personal_events = []
                if debug:
                    print(f"[DEBUG] Apple Calendar events fetched: {len(msi_blocks)}")
                    for b in msi_blocks:
                        loc = f" @ {b['location']}" if b.get("location") else ""
                        print(f"[DEBUG]   {b['start'].strftime('%H:%M')} – {b['end'].strftime('%H:%M')} — {b['title']}{loc}")
            except Exception as exc:
                _reason = str(exc)
                print(f"[sync_job] Apple Calendar read failed, falling back to Google: {_reason}", file=sys.stderr)
                try:
                    rumps.notification(
                        "Phantom Calendar", "",
                        f"Apple Calendar read failed: {_reason} — using Google Calendar",
                    )
                except Exception:
                    pass
                use_apple = False
                msi_blocks = get_msi_time_blocks(target_date=target_date)
                personal_events = get_personal_events(target_date=target_date)
                if debug:
                    print(f"[DEBUG] Fallback: MSI blocks fetched: {len(msi_blocks)}")
        else:
            msi_blocks = get_msi_time_blocks(target_date=target_date)
            if debug:
                print(f"[DEBUG] MSI blocks fetched: {len(msi_blocks)}")
                for b in msi_blocks:
                    print(
                        f"[DEBUG]   {b['start'].strftime('%H:%M')} – {b['end'].strftime('%H:%M')}"
                    )

            personal_events = get_personal_events(target_date=target_date)
            if debug:
                print(f"[DEBUG] Personal events fetched: {len(personal_events)}")
                for e in personal_events:
                    loc = f" @ {e['location']}" if e.get("location") else ""
                    print(f"[DEBUG]   {e['start'].strftime('%H:%M')} — {e['title']}{loc}")

        result = compute_alarm(msi_blocks, personal_events, config, debug=debug)
        # Attach raw personal events so _show_popup can pass them to _classify_personal_events
        # (Apple path: personal_events=[] so this is a no-op; Google path: unchanged)
        result["personal_events"] = [
            e for e in personal_events if "Alarm" not in e.get("title", "")
        ]
        alarm_time = result.get("alarm_time")

        if debug:
            print("[DEBUG] --- Alarm result ---")
            print(f"[DEBUG] First meeting : {result.get('first_meeting_name')}")
            mt = result.get("first_meeting_time")
            print(f"[DEBUG] Meeting time  : {mt.strftime('%H:%M') if mt else 'N/A'}")
            print(f"[DEBUG] Prep minutes  : {result.get('prep_minutes')}")
            at = result.get("alarm_time")
            print(f"[DEBUG] Alarm time    : {at.strftime('%H:%M') if at else 'N/A'}")
            print(f"[DEBUG] Is baseline   : {result.get('is_baseline')}")
            print(
                f"[DEBUG] All candidates: {[c['name'] for c in result.get('all_meetings', [])]}"
            )
            print(f"[DEBUG] Unknown blocks: {len(result.get('unknown_blocks', []))}")

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

        # Write new location → travel-minutes mappings to Drive config (non-fatal)
        if popup_response.get("location_travel_minutes"):
            try:
                append_locations(popup_response["location_travel_minutes"], config)
                print(
                    f"[sync_job] Wrote {len(popup_response['location_travel_minutes'])} "
                    "location(s) to Drive config."
                )
            except Exception as exc:
                print(f"[sync_job] WARNING: Could not write locations to Drive — {exc}", file=sys.stderr)

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
