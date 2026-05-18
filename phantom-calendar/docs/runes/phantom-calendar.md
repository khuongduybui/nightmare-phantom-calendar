# Rune: phantom-calendar

Component-scoped rules for the `phantom-calendar/` project.
Apply during Implementer, QA, Story-Review, and Feature-Review phases.

---

## Rule: update-build-tests-sh

**When:** Any user story adds, renames, or removes test files under `tests/`.
**Action:** Verify `build/tests.sh` still discovers and runs all test files. The script uses `python -m pytest tests/ -v` which auto-discovers, so no edit is needed unless the `tests/` layout changes structurally (e.g., subdirectories added).
**Owner:** Feature-Review

---

## Rule: update-manual-tests-md

**When:** Any user story introduces manual acceptance criteria (ACs marked "manual" or "requires human verification").
**Action:** Add a new entry to `build/manual_tests.md` following the existing format:
- Unique ID: `MT-{feature_number}.{ac_number}`
- Sections: Feature, Prerequisites, Steps, Pass criteria
**Owner:** Implementer (draft) → Feature-Review (verify completeness)

---

## Rule: update-readme

**When:** Any of the following change:
- New runtime dependencies added to `requirements.txt`
- New source files added to the project root
- New sections added to `build/manual_tests.md`
- Setup steps change (OAuth scopes, GCP configuration, etc.)
**Action:** Update the relevant section of `README.md` (Setup, Project Structure table, Manual tests table, or Security Notes).
**Owner:** Feature-Review

---

## Rule: no-credentials-in-git

**When:** Any phase (always enforced).
**Action:** Verify `credentials.json` and `token.json` are absent from all staged/committed files. Both must remain in `.gitignore`. Fail the review if either appears in the diff.
**Owner:** Story-Review, Feature-Review

---

## Rule: python-version-compatibility

**When:** Any new Python code is written.
**Action:** Do not use APIs deprecated or removed in Python 3.14. In particular:
- Use `datetime.now(tz=timezone.utc)` not `datetime.utcnow()` (removed in 3.12+)
- Check https://docs.python.org/3.14/whatsnew/ for removals
**Owner:** Implementer, QA

---

## Rule: venv-and-uv-conventions

**When:** Any phase that runs or documents Python commands.
**Action:** Use the project-standard environment setup:
- Shell: **fish** (default)
- venv location: at the **git common root** — `(dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv/`
- Create venv: `uv venv --python 3.14 (dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv`
- Activate (fish): `source (dirname (git rev-parse --git-common-dir))/phantom-calendar/.venv/bin/activate.fish`
- Install packages: `uv pip install ...`
- Run scripts: `uv run <script>`
- Never use bare `python`, `python3`, or `pip` — always `uv run` or `uv pip`.
**Owner:** Implementer, QA, Story-Review, Feature-Review

---

## Rule: icon-design-consistency

**When:** Any feature introduces a new visual state for the menu bar app (new icon needed).
**Action:**
1. Generate the new icon using the **same alarm clock base silhouette** defined in `docs/NPC-0009/feature.md`. All icons must share this base — only the overlay badge/annotation changes.
2. Use the Gemini image generation prompts in `docs/NPC-0009/feature.md` as a template, adapting only the overlay description.
3. Spec: 72×72 px (36pt @2x Retina), **white** monochrome line art on transparent background, single stroke weight, no fill, no gradients. Use white (not black) — rumps does not call `setTemplate_(True)` so icons are not auto-inverted; white is visible on dark menu bars and macOS dims white icons appropriately on light bars.
4. Place the new PNG in `assets/` and update `app.py` to reference it in the correct state handler.
5. Update `README.md` icon table with the new state.

**Owner:** Implementer, Feature-Review

---
## Rule: no-tkinter-in-rumps-process

**When:** Any feature introduces UI shown while the rumps app is running (menu callbacks, sync pipeline, background threads).
**Action:** Do NOT use `tkinter` (`tk.Tk()`, `tk.mainloop()`) inside the running app. AppKit's `NSRunLoop` owns the main thread and `TkpGetColor` requires it — tkinter crashes with `NSInvalidArgumentException` from any thread inside a rumps process.
- **Sync pipeline UI** (background thread): use `subprocess.run(["osascript", ...])` dialogs.
- **Menu callback UI** (main thread): also use osascript — tkinter's `macOSVersion` selector still fails even on the main thread within AppKit.
- **Preferences/settings**: use sequential osascript `display dialog` / `choose from list` calls.
- `popup.py` has been removed. Use `sync_job._show_popup()` and `preferences.PreferencesWindow` (both osascript-based) as the established pattern.
**Owner:** Implementer, QA

---

## Rule: no-heredoc-in-fish

**When:** Any shell command needs to write multi-line content to a file.
**Action:** Fish shell does NOT support `<<` heredoc syntax. Use one of these alternatives:
- `echo "content" > file` for single-line content
- Python one-liner: `uv run python -c "open('file','w').write('content')"`
- The file creation tools in the agent (preferred for new files)
**Owner:** Implementer

---

## Rule: local-state-files-in-gitignore

**When:** Any feature introduces a local state or cache file that persists across runs.
**Action:** Add the file to `.gitignore`. Confirmed exclusions: `credentials.json`, `token.json`, `.drive_config_id`, `.phantom_state.json`. Pattern: dot-files at project root that hold runtime state are never committed.
**Owner:** Implementer, Story-Review

---

## Rule: logging-module-only

**When:** Any code writes diagnostic, info, warning, or error output.
**Action:** Use the `logging` module exclusively. No `print()` for diagnostics. No writing to `sys.stderr` directly. No ad-hoc helper functions (`_dbg`, `_log`, etc.).
**Owner:** Implementer, QA, Story-Review

---

## Rule: module-level-logger

**When:** Any production module (`*.py` under `phantom-calendar/`, excluding `tests/`) needs to emit log output.
**Action:** Declare exactly one module-level logger at the top of the file, after imports:
```python
import logging
logger = logging.getLogger(__name__)
```
Use `logger.*()` for all calls within that module. Never call `logging.debug(...)` / `logging.info(...)` etc. at the module level directly — always go through the named logger.
**Owner:** Implementer

---

## Rule: logging-config-entry-points-only

**When:** Any module needs to configure log output format, level, or handlers.
**Action:** Call `logging.basicConfig()` only in `main.py` and `app.py` (the two entry points), via a shared `configure_logging()` helper defined in `main.py`. Library modules (`sync_job.py`, `compute.py`, `drive_config.py`, `calendar_writer.py`, `apple_calendar.py`, `osaurus_client.py`) must not call `basicConfig()`, add handlers, or set logger levels.
**Owner:** Implementer, QA

---

## Rule: phantom-debug-env-var

**When:** Any code needs verbose debug output gated on an environment variable.
**Action:** Use `PHANTOM_DEBUG=1` as the single project-wide flag. The `configure_logging()` function in `main.py` reads this env var and sets the root logger to `DEBUG` level. Do not introduce per-module env flags (e.g. `PHANTOM_APPLE_DEBUG` is removed and must not be re-added).
**Owner:** Implementer

---

## Rule: logging-levels

**When:** Choosing a log level for any new log call.
**Action:**
- `logger.debug()` — verbose internals: probe results, event lists, computed values
- `logger.info()` — normal flow milestones: config loaded, alarm written, scheduler started
- `logger.warning()` — non-fatal anomalies: fallback activated, config mirror failed, classification write failed
- `logger.error()` or `logger.exception()` — caught exceptions on error paths that surface to the user
**Owner:** Implementer, QA

---

## Rule: test-logging-with-assertlogs

**When:** Any test verifies that a warning or error is emitted by production code.
**Action:** Use `self.assertLogs("<logger-name>", level="WARNING")` (or `ERROR`). Do **not** patch `sys.stderr` to capture log output — that no longer works after the `logging` migration. Use `log_ctx.records` for exact count checks and `log_ctx.output` for message content checks.

Logger names follow `__name__`, so:
- `main.py` → `"main"` (not `"__main__"` — it is imported as a module in tests)
- `osaurus_client.py` → `"osaurus_client"`
- `sync_job.py` → `"sync_job"`

**Owner:** Implementer, QA
