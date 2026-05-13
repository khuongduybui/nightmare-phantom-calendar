"""Preferences window — allows the user to edit core settings via a tkinter form.

Safe to call from a rumps menu callback because rumps schedules menu callbacks
on the main thread, unlike the sync pipeline which runs on a background thread.
"""

import re
import tkinter as tk


class PreferencesWindow:
    """Tkinter form for editing the 5 core config settings.

    Usage:
        result = PreferencesWindow(config).show()
        # result: dict with updated values, or None if cancelled
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._result: dict | None = None
        self._root: tk.Tk | None = None

    def show(self) -> dict | None:
        """Open the preferences window and block until the user saves or cancels."""
        self._root = tk.Tk()
        self._root.title("Phantom Calendar — Preferences")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._root.lift()
        self._root.attributes("-topmost", True)
        self._root.focus_force()

        self._build_ui()
        self._root.mainloop()
        return self._result

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 4}

        tk.Label(self._root, text="Preferences", font=("System", 14, "bold")).pack(pady=(12, 4))

        frame = tk.Frame(self._root)
        frame.pack(fill="x", padx=16, pady=4)

        fields = [
            ("Trigger time (HH:MM):", "daily_run_time",
             self._config.get("daily_run_time", "21:00")),
            ("Timezone:", "timezone",
             self._config.get("timezone", "America/New_York")),
            ("Default prep minutes:", "default_prep_minutes",
             str(self._config.get("default_prep_minutes", 30))),
            ("Personal calendar ID:", "personal_calendar_id",
             self._config.get("personal_calendar_id", "")),
            ("MSI Work calendar ID:", "msi_calendar_id",
             self._config.get("msi_calendar_id", "")),
        ]

        self._entries: dict[str, tk.Entry] = {}
        for i, (label_text, key, value) in enumerate(fields):
            tk.Label(frame, text=label_text, anchor="w", width=24).grid(
                row=i, column=0, sticky="w", pady=3
            )
            entry = tk.Entry(frame, width=36)
            entry.insert(0, value)
            entry.grid(row=i, column=1, pady=3, padx=(8, 0))
            self._entries[key] = entry

        # Error label
        self._error_label = tk.Label(self._root, text="", fg="red")
        self._error_label.pack(padx=16)

        # Buttons
        btn_frame = tk.Frame(self._root)
        btn_frame.pack(pady=(4, 12))

        save_btn = tk.Button(btn_frame, text="Save", command=self._on_save,
                             takefocus=True)
        save_btn.bind("<Return>", lambda _e: self._on_save())
        save_btn.pack(side="left", padx=8)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._on_cancel,
                               takefocus=True)
        cancel_btn.bind("<Return>", lambda _e: self._on_cancel())
        cancel_btn.pack(side="left", padx=8)

        # Focus first entry
        self._root.after(100, lambda: self._entries["daily_run_time"].focus_set())

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        """Validate inputs; close and return updated config on success."""
        values = {key: entry.get().strip() for key, entry in self._entries.items()}

        # Validate trigger time
        if not re.match(r"^(\d{2}):(\d{2})$", values["daily_run_time"]):
            self._error_label.config(text="Trigger time must be HH:MM (e.g. 21:00)")
            return
        hh, mm = map(int, values["daily_run_time"].split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            self._error_label.config(text="Trigger time out of range (00:00 – 23:59)")
            return

        # Validate prep minutes
        try:
            prep = int(values["default_prep_minutes"])
            if prep <= 0:
                raise ValueError
        except ValueError:
            self._error_label.config(text="Default prep minutes must be a positive integer")
            return

        self._error_label.config(text="")
        self._result = {
            "daily_run_time": values["daily_run_time"],
            "timezone": values["timezone"],
            "default_prep_minutes": prep,
            "personal_calendar_id": values["personal_calendar_id"],
            "msi_calendar_id": values["msi_calendar_id"],
        }
        self._root.destroy()

    def _on_cancel(self) -> None:
        """Close window without saving."""
        self._result = None
        self._root.destroy()
