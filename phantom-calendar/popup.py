"""Confirmation popup — shows computed alarm result and returns user response."""

from datetime import datetime

# tkinter is imported lazily inside show() so that this module can be imported
# (and unit-tested with mocks) in environments where Tk is not installed.
tk = None  # populated at runtime by _import_tk()


class ConfirmationPopup:
    """Modal tkinter window for confirming tomorrow's alarm time.

    Args:
        result: The dict returned by compute_alarm().

    Usage:
        response = ConfirmationPopup(result).show()
        # response: {"confirmed": bool, "alarm_time": datetime|None, "skipped": bool}
    """

    def __init__(self, result: dict) -> None:
        self._result = result
        self._response: dict = {
            "confirmed": False,
            "alarm_time": None,
            "skipped": False,
        }
        self._root: tk.Tk | None = None
        self._alarm_entry: tk.Entry | None = None
        self._error_label: tk.Label | None = None
        self._warning_label: tk.Label | None = None
        self._write_btn: tk.Button | None = None

        # Determine display mode
        if result.get("first_meeting_name") is None:
            self._mode = "no_meetings"
        elif result.get("is_baseline"):
            self._mode = "baseline"
        else:
            self._mode = "normal"

    def show(self) -> dict:
        """Open the popup and block until the user responds."""
        global tk
        if tk is None:
            import tkinter as _tk

            tk = _tk
        self._root = tk.Tk()
        self._root.title("Phantom Calendar — Nightly Sync")
        self._root.resizable(False, False)

        self._build_ui()

        # Ensure window appears in front
        self._root.lift()
        self._root.attributes("-topmost", True)
        self._root.focus_force()

        # Bind OS close button
        if self._mode == "normal":
            self._root.protocol("WM_DELETE_WINDOW", self._on_confirm)
        else:
            self._root.protocol("WM_DELETE_WINDOW", self._on_skip)

        self._root.mainloop()
        return self._response

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 6}

        tk.Label(
            self._root,
            text="Tomorrow's Alarm",
            font=("System", 15, "bold"),
        ).pack(**pad)

        # Unknown blocks warning (all modes)
        unknown = self._result.get("unknown_blocks") or []
        if unknown:
            lines = "\n".join(
                f"Unknown block at {b['start'].strftime('%H:%M')} — "
                f"{self._result.get('default_prep_minutes', 30)} min prep applied"
                for b in unknown
            )
            self._warning_label = tk.Label(
                self._root,
                text=lines,
                fg="orange",
                justify="left",
            )
            self._warning_label.pack(**pad)

        if self._mode == "no_meetings":
            self._build_no_meetings()
        elif self._mode == "baseline":
            self._build_baseline()
        else:
            self._build_normal()

        # Buttons
        btn_frame = tk.Frame(self._root)
        btn_frame.pack(pady=10)

        if self._mode == "normal":
            self._write_btn = tk.Button(
                btn_frame,
                text="Write to Calendar",
                command=self._on_confirm,
            )
            self._write_btn.pack(side="left", padx=6)

        tk.Button(btn_frame, text="Skip", command=self._on_skip).pack(
            side="left", padx=6
        )

    def _build_no_meetings(self) -> None:
        tk.Label(
            self._root,
            text="No meetings found for tomorrow.",
            fg="gray",
        ).pack(padx=16, pady=4)

    def _build_baseline(self) -> None:
        result = self._result
        tk.Label(
            self._root, text=f"First meeting: {result['first_meeting_name']}"
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text=f"Meeting time: {result['first_meeting_time'].strftime('%H:%M')}",
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text=f"Prep time: {result['prep_minutes']} min",
            fg="gray",
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text=f"Alarm: {result['alarm_time'].strftime('%H:%M')}",
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text="✓ Matches baseline — no new calendar event needed.",
            fg="green",
        ).pack(padx=16, pady=4, anchor="w")

    def _build_normal(self) -> None:
        result = self._result
        tk.Label(
            self._root, text=f"First meeting: {result['first_meeting_name']}"
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text=f"Meeting time: {result['first_meeting_time'].strftime('%H:%M')}",
        ).pack(padx=16, pady=2, anchor="w")
        tk.Label(
            self._root,
            text=f"Prep time: {result['prep_minutes']} min",
            fg="gray",
        ).pack(padx=16, pady=2, anchor="w")

        alarm_frame = tk.Frame(self._root)
        alarm_frame.pack(padx=16, pady=4, anchor="w")
        tk.Label(alarm_frame, text="Alarm time:").pack(side="left")
        self._alarm_entry = tk.Entry(alarm_frame, width=8, justify="center")
        self._alarm_entry.insert(0, result["alarm_time"].strftime("%H:%M"))
        self._alarm_entry.pack(side="left", padx=6)

        self._error_label = tk.Label(self._root, text="", fg="red")
        self._error_label.pack(padx=16)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        """Handle 'Write to Calendar' click or window dismiss in normal mode."""
        alarm_time = self._parse_alarm_override(
            self._alarm_entry.get() if self._alarm_entry else "",
            self._result["first_meeting_time"],
        )
        if alarm_time is None:
            if self._error_label:
                self._error_label.config(text="Invalid time — use HH:MM (e.g. 09:25)")
            return
        if self._error_label:
            self._error_label.config(text="")
        self._response = {"confirmed": True, "alarm_time": alarm_time, "skipped": False}
        self._root.destroy()

    def _on_skip(self) -> None:
        """Handle 'Skip' click or window dismiss in baseline/no-meetings mode."""
        if self._mode == "baseline":
            self._response = {"confirmed": False, "alarm_time": None, "skipped": False}
        else:
            self._response = {"confirmed": False, "alarm_time": None, "skipped": True}
        self._root.destroy()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_alarm_override(
        self, text: str, reference_dt: datetime
    ) -> datetime | None:
        """Parse HH:MM string into a tz-aware datetime on reference_dt's date.

        Returns None if the text is not a valid HH:MM time.
        """
        if not text or ":" not in text:
            return None
        parts = text.strip().split(":")
        if len(parts) != 2:
            return None
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return None
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return reference_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
