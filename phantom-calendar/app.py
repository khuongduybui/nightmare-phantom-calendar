"""Phantom Calendar macOS menu bar application."""

import json
import os
import subprocess
import sys
import threading
from datetime import datetime

import pytz
import rumps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, ".phantom_state.json")

from drive_config import parse_config, read_config, write_config
from preferences import PreferencesWindow
from scheduler import check_and_run_missed_sync, start_scheduler
from sync_job import queue_run, run_nightly_sync

_PREFS_OPEN = threading.Lock()


class PhantomCalendarApp(rumps.App):
    """Menu bar application with nightly sync scheduler and status display."""

    ICON_IDLE = "assets/icon.png"
    ICON_SYNCING = "assets/icon_syncing.png"

    def _set_icon(self, path: str) -> None:
        """Set the menu bar icon."""

        self.icon = path
    ICON_ERROR = "assets/icon_error.png"

    def __init__(self):
        super().__init__(
            name="Phantom Calendar",
            icon=self.ICON_IDLE,
            quit_button="Quit",
        )

        # In-memory sync state
        self._last_run_time: datetime | None = None
        self._last_alarm_time: datetime | None = None
        self._last_sync_failed: bool = False
        self._timezone_str: str = "America/New_York"

        # Status menu items (non-clickable)
        self._last_run_item = rumps.MenuItem("Last run: —")
        self._last_alarm_item = rumps.MenuItem("Alarm: —")

        self.menu = [
            self._last_run_item,
            self._last_alarm_item,
            None,  # separator
            rumps.MenuItem("Preferences…", callback=self.show_preferences),
            rumps.MenuItem("Run now", callback=self.run_now),
        ]

        # Restore last run state from disk (non-fatal if missing/corrupt)
        self._load_state()

        # Load config once at startup to get timezone and trigger time for scheduler
        self._trigger_time: str = "21:00"
        try:
            config = parse_config(read_config())
            self._timezone_str = config.get("timezone", "America/New_York")
            self._trigger_time = config.get("daily_run_time", "21:00")
        except Exception as exc:
            print(f"[app] WARNING: Could not load config at startup — {exc}", file=sys.stderr)

        # Register as Login Item on first launch (non-fatal)
        self._register_login_item()

        # Run a missed sync if trigger time has already passed today
        check_and_run_missed_sync(self._timezone_str)

        # Start the background scheduler
        self._scheduler = start_scheduler(self._timezone_str, self._trigger_time)

        # Icon is already set via self.icon= in _load_state() or defaults to ICON_IDLE from super().__init__

    def __del__(self):
        if hasattr(self, "_scheduler") and self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Sync state callbacks
    # ------------------------------------------------------------------

    def set_syncing(self, syncing: bool) -> None:
        """Update the menu bar icon to reflect sync-in-progress state."""
        if syncing:
            self._set_icon(self.ICON_SYNCING)
        else:
            self._set_icon(self.ICON_ERROR if self._last_sync_failed else self.ICON_IDLE)

    def update_sync_state(self, alarm_time: datetime | None, failed: bool) -> None:
        """Update status menu items and icon after a sync completes."""
        tz = pytz.timezone(self._timezone_str)
        now = datetime.now(tz)

        self._last_run_time = now
        self._last_alarm_time = alarm_time
        self._last_sync_failed = failed

        self._last_run_item.title = f"Last run: {now.strftime('%-I:%M %p')}"
        if alarm_time:
            self._last_alarm_item.title = f"Alarm: {alarm_time.strftime('%-I:%M %p')}"
        else:
            self._last_alarm_item.title = "Alarm: none"

        self._set_icon(self.ICON_ERROR if failed else self.ICON_IDLE)
        self._save_state()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        """Persist sync state to .phantom_state.json (non-fatal on error)."""
        try:
            state = {
                "last_run_time": self._last_run_time.isoformat() if self._last_run_time else None,
                "last_alarm_time": self._last_alarm_time.isoformat() if self._last_alarm_time else None,
                "last_sync_failed": self._last_sync_failed,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
        except Exception as exc:
            print(f"[app] WARNING: Could not save state — {exc}", file=sys.stderr)

    def _load_state(self) -> None:
        """Restore sync state from .phantom_state.json (non-fatal if missing/corrupt)."""
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except FileNotFoundError:
            return
        except Exception as exc:
            print(f"[app] WARNING: Could not load state — {exc}", file=sys.stderr)
            return

        try:
            raw_run = state.get("last_run_time")
            raw_alarm = state.get("last_alarm_time")
            self._last_run_time = datetime.fromisoformat(raw_run) if raw_run else None
            self._last_alarm_time = datetime.fromisoformat(raw_alarm) if raw_alarm else None
            self._last_sync_failed = bool(state.get("last_sync_failed", False))

            if self._last_run_time:
                self._last_run_item.title = f"Last run: {self._last_run_time.strftime('%-I:%M %p')}"
            if self._last_alarm_time:
                self._last_alarm_item.title = f"Alarm: {self._last_alarm_time.strftime('%-I:%M %p')}"
            elif self._last_run_time:
                # A sync ran but no alarm was set
                self._last_alarm_item.title = "Alarm: none"

            if self._last_sync_failed:
                self._set_icon(self.ICON_ERROR)
        except Exception as exc:
            print(f"[app] WARNING: Could not parse saved state — {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def show_preferences(self, _):
        """Open the preferences window in a background thread (single-instance guard).

        tkinter's mainloop conflicts with AppKit's NSRunLoop on the main thread in rumps.
        Running PreferencesWindow in a daemon thread sidesteps this — tkinter still
        works because it's the only UI framework running in that thread.
        """
        if not _PREFS_OPEN.acquire(blocking=False):
            return  # already open

        def _run():
            try:
                try:
                    config = parse_config(read_config())
                except Exception as exc:
                    print(f"[app] WARNING: Could not load config for prefs — {exc}", file=sys.stderr)
                    config = {}
                result = PreferencesWindow(config).show()
                if result is not None:
                    self._save_preferences(result)
            finally:
                _PREFS_OPEN.release()

        threading.Thread(target=_run, daemon=True).start()

    def _save_preferences(self, updated: dict) -> None:
        """Write updated settings to Drive config and restart the scheduler."""
        try:
            import yaml
            config = parse_config(read_config())
            # Update only the 5 preference fields
            config["personal_calendar_id"] = updated["personal_calendar_id"]
            config["msi_calendar_id"] = updated["msi_calendar_id"]
            config["timezone"] = updated["timezone"]
            config["default_prep_minutes"] = updated["default_prep_minutes"]
            config["daily_run_time"] = updated["daily_run_time"]
            # Rebuild YAML preserving all other fields
            data = {
                "calendars": {
                    "personal_id": config["personal_calendar_id"],
                    "msi_id": config["msi_calendar_id"],
                    "daily_run_time": config["daily_run_time"],
                },
                "timezone": config["timezone"],
                "default_prep_minutes": config["default_prep_minutes"],
                "baseline_event": {
                    "id": config.get("baseline_event_id", ""),
                    "title": config.get("baseline_event_title", ""),
                    "time": config.get("baseline_event_time", "09:25"),
                },
                "recurring_meetings": config.get("recurring_meetings") or [],
                "meeting_type_prep": config.get("meeting_type_prep") or {},
                "locations": config.get("locations") or {},
                "client_overrides": config.get("client_overrides") or {},
            }
            write_config(yaml.dump(data, default_flow_style=False, allow_unicode=True))
            self._restart_scheduler(updated["timezone"], updated["daily_run_time"])
            print("[app] Preferences saved and scheduler restarted.")
        except Exception as exc:
            print(f"[app] ERROR: Could not save preferences — {exc}", file=sys.stderr)
            try:
                rumps.notification("Phantom Calendar", "", f"Could not save preferences: {exc}")
            except Exception:
                pass

    def _restart_scheduler(self, timezone_str: str, trigger_time: str) -> None:
        """Shut down the current scheduler and start a new one with updated settings."""
        if hasattr(self, "_scheduler") and self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        self._timezone_str = timezone_str
        self._trigger_time = trigger_time
        self._scheduler = start_scheduler(timezone_str, trigger_time)
        print(f"[app] Scheduler restarted: {trigger_time} {timezone_str}")

    @rumps.clicked("Run now")
    def run_now(self, _):
        threading.Thread(
            target=queue_run, kwargs={"app_ref": self}, daemon=True
        ).start()

    # ------------------------------------------------------------------
    # Login Item registration
    # ------------------------------------------------------------------

    def _register_login_item(self) -> None:
        """Register the app as a macOS Login Item (non-fatal on failure)."""
        try:
            app_path = os.path.abspath(sys.argv[0])
            script = (
                f'tell application "System Events" to make login item at end '
                f'with properties {{path:"{app_path}", hidden:false}}'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                print(
                    f"[app] WARNING: Login Item registration failed — "
                    f"{result.stderr.decode().strip()}",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"[app] WARNING: Login Item registration failed — {exc}", file=sys.stderr)
