"""Preferences window — sequential osascript dialogs for editing core settings."""

import re
import subprocess


def _osascript(script: str) -> tuple[str, int]:
    """Run an AppleScript snippet. Returns (stdout.strip(), returncode)."""
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.stdout.strip(), proc.returncode


def _ask(
    prompt: str, default: str, title: str = "Phantom Calendar — Preferences"
) -> str | None:
    """Show a text-input dialog. Returns entered text or None if cancelled."""
    script = (
        f'tell application "System Events"\n'
        f'  set r to display dialog "{prompt}" '
        f'default answer "{default}" '
        f'buttons {{"Cancel", "Next"}} '
        f'default button "Next" '
        f'with title "{title}"\n'
        f'  if button returned of r is "Cancel" then return "__cancel__"\n'
        f"  return text returned of r\n"
        f"end tell"
    )
    out, rc = _osascript(script)
    if rc != 0 or out == "__cancel__":
        return None
    return out.strip()


class PreferencesWindow:
    """Sequential osascript dialogs for editing the 5 core config settings.

    Shows one field at a time. User can cancel at any step.

    Usage:
        result = PreferencesWindow(config).show()
        # result: dict with updated values, or None if cancelled
    """

    def __init__(self, config: dict) -> None:
        self._config = config

    def show(self) -> dict | None:
        """Walk through the 5 settings fields one by one. Returns dict or None."""
        c = self._config

        fields = [
            (
                "daily_run_time",
                f"Trigger time (HH:MM)\\n\\nCurrent: {c.get('daily_run_time', '21:00')}",
                c.get("daily_run_time", "21:00"),
            ),
            (
                "timezone",
                f"Timezone (e.g. America/New_York)\\n\\nCurrent: {c.get('timezone', 'America/New_York')}",
                c.get("timezone", "America/New_York"),
            ),
            (
                "default_prep_minutes",
                f"Default prep minutes (positive integer)\\n\\nCurrent: {c.get('default_prep_minutes', 30)}",
                str(c.get("default_prep_minutes", 30)),
            ),
            (
                "personal_calendar_id",
                f"Personal calendar ID (Gmail address)\\n\\nCurrent: {c.get('personal_calendar_id', '')}",
                c.get("personal_calendar_id", ""),
            ),
            (
                "msi_calendar_id",
                f"MSI Work calendar ID\\n\\nCurrent: {c.get('msi_calendar_id', '')}",
                c.get("msi_calendar_id", ""),
            ),
        ]

        values: dict = {}
        for key, prompt, default in fields:
            val = _ask(prompt, default)
            if val is None:
                return None  # user cancelled
            values[key] = val

        # Normalize trigger time: accept decimal hours (e.g. 22.5 → 22:30, 9 → 09:00)
        raw_time = values["daily_run_time"].strip()
        if not re.match(r"^\d{1,2}:\d{2}$", raw_time):
            try:
                hours_float = float(raw_time)
                hh_int = int(hours_float)
                mm_int = round((hours_float - hh_int) * 60)
                if mm_int == 60:
                    hh_int += 1
                    mm_int = 0
                raw_time = f"{hh_int:02d}:{mm_int:02d}"
            except ValueError:
                pass
        values["daily_run_time"] = raw_time

        # Validate trigger time
        if not re.match(r"^\d{2}:\d{2}$", values["daily_run_time"]):
            _osascript(
                'tell application "System Events" to display dialog '
                '"Invalid trigger time — must be HH:MM (e.g. 21:00). '
                'Changes not saved." buttons {"OK"} '
                'with title "Phantom Calendar — Preferences"'
            )
            return None
        hh, mm = map(int, values["daily_run_time"].split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            _osascript(
                'tell application "System Events" to display dialog '
                '"Trigger time out of range (00:00 – 23:59). '
                'Changes not saved." buttons {"OK"} '
                'with title "Phantom Calendar — Preferences"'
            )
            return None

        # Validate prep minutes
        try:
            prep = int(values["default_prep_minutes"])
            if prep <= 0:
                raise ValueError
        except ValueError:
            _osascript(
                'tell application "System Events" to display dialog '
                '"Default prep minutes must be a positive integer. '
                'Changes not saved." buttons {"OK"} '
                'with title "Phantom Calendar — Preferences"'
            )
            return None

        return {
            "daily_run_time": values["daily_run_time"],
            "timezone": values["timezone"],
            "default_prep_minutes": prep,
            "personal_calendar_id": values["personal_calendar_id"],
            "msi_calendar_id": values["msi_calendar_id"],
        }
