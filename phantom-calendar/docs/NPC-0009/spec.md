---
spec_hash: 'ba25c3ccc293'
---

# NPC-0009 Spec — Custom Icon Design

## Clarifications from Codebase

### Current State (emoji titles)

`app.py` currently uses `rumps.App(title="⏰")` and swaps the `title` string for each state:
- Normal: `self.title = "⏰"`
- Syncing: `self.title = "⏳"`
- Error: `self.title = "⏰❌"`

### Target State (template images)

Replace all `self.title` icon assignments with `self.icon` pointing to PNG files in `assets/`:

| File | State | Trigger |
|---|---|---|
| `assets/icon.png` | Idle | default / `set_syncing(False)` success |
| `assets/icon_syncing.png` | Sync in progress | `set_syncing(True)` |
| `assets/icon_error.png` | Last sync failed | `update_sync_state(failed=True)`, `_load_state(failed=True)` |

### How rumps handles icons

`rumps.App(icon="path/to/icon.png")` sets the menu bar image. `self.icon = "path"` updates it at runtime. rumps passes it directly to AppKit as a template image — macOS auto-inverts for dark mode when the image is purely black-on-transparent.

### Code locations to change

All in `app.py`:
- `PhantomCalendarApp.__init__()` — `super().__init__(..., title="⏰")` → `icon="assets/icon.png"`; remove `title=`
- `set_syncing(syncing)` — replace `self.title = "⏳"` / `"⏰❌"` / `"⏰"` with `self.icon = ...`
- `update_sync_state(alarm_time, failed)` — replace `self.title = "⏰❌"` / `"⏰"` with `self.icon = ...`
- `_load_state()` — replace `self.title = "⏰❌"` with `self.icon = "assets/icon_error.png"`

---

## ⚠️ Human-Required Steps — Icon Generation

These steps **must be completed by the developer** before any code is written. AI cannot generate image files.

### H-1 — Generate the three icons using Gemini

Go to [Google Gemini](https://gemini.google.com) or Gemini Advanced. Generate each icon separately using the prompts below. Download each result.

#### H-1a — Normal / idle icon (`assets/icon.png`)

Use this prompt verbatim:

> Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.
>
> Design: A simple alarm clock silhouette — circular clock face with two small bells on top and a single bell-hammer in the center bottom. The clock hands point to approximately 9 o'clock. Minimal detail, single stroke weight, no gradients, no shadows.

Save the result as: `phantom-calendar/assets/icon.png`

#### H-1b — Syncing icon (`assets/icon_syncing.png`)

Use this prompt verbatim (references the same base design):

> Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.
>
> Design: The same alarm clock silhouette as icon.png (circular face, two bells on top, bell-hammer bottom, hands at ~9:00), but with two curved arrows forming a circular refresh/sync symbol overlaid in the bottom-right quadrant of the clock face. The refresh arrows should be roughly 1/3 the clock diameter and clearly convey "in progress" or "syncing". Single stroke weight, no gradients, no shadows. Consistent stroke weight with the base icon.

Save the result as: `phantom-calendar/assets/icon_syncing.png`

#### H-1c — Error icon (`assets/icon_error.png`)

Use this prompt verbatim:

> Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.
>
> Design: The same alarm clock silhouette as icon.png (circular face, two bells on top, bell-hammer bottom, hands at ~9:00), but with a small exclamation mark (!) inside a filled circle badge in the bottom-right corner of the icon. The badge circle should be solid black, the exclamation mark white/cutout, and sized so it is clearly readable at 18pt on a Retina display. Single stroke weight, consistent with the base icon.

Save the result as: `phantom-calendar/assets/icon_error.png`

### H-2 — Verify icon quality

Before writing any code, open each PNG and confirm:

1. **Transparency**: background is transparent (checkerboard pattern in Preview), not white.
2. **Size**: 36×36 pixels (File → Get Info → More Info in Preview).
3. **Monochrome**: image is purely black — no color, no gray gradients.
4. **Consistency**: all three icons clearly share the same alarm clock base — overlay elements (arrows, badge) are visually distinct and readable at small size.
5. **Macintosh test**: drag each PNG onto the desktop, switch between light and dark mode — the icon should invert cleanly. If it does not (e.g. the background turns white), the image has a white fill instead of transparency.

If any icon fails, regenerate with the same prompt. Add the phrase "ensure the background is fully transparent with no white fill" if the transparency check fails.

### H-3 — Place files

After H-2 passes, the files must be at these exact paths:
```
phantom-calendar/assets/icon.png
phantom-calendar/assets/icon_syncing.png
phantom-calendar/assets/icon_error.png
```
The `assets/` directory does **not** exist yet — create it.

---

## User Stories

---

### US-1 — Wire Icons into app.py

**Story:** As a user, I want the menu bar to display proper monochrome PNG icons instead of emoji so the app looks native on macOS in both light and dark mode.

**Acceptance Criteria:**

- AC1.1: `assets/icon.png`, `assets/icon_syncing.png`, `assets/icon_error.png` exist (placed by developer per H-1 through H-3).
- AC1.2: `PhantomCalendarApp.__init__()` uses `icon="assets/icon.png"` and does NOT set `title=` for the icon character.
- AC1.3: `set_syncing(True)` sets `self.icon = "assets/icon_syncing.png"`.
- AC1.4: `set_syncing(False)` sets `self.icon = "assets/icon_error.png"` if `_last_sync_failed` else `"assets/icon.png"`.
- AC1.5: `update_sync_state(alarm_time, failed=True)` sets `self.icon = "assets/icon_error.png"`.
- AC1.6: `update_sync_state(alarm_time, failed=False)` sets `self.icon = "assets/icon.png"`.
- AC1.7: `_load_state()` sets `self.icon = "assets/icon_error.png"` when restoring a failed state, otherwise `"assets/icon.png"`.
- AC1.8: No `datetime.utcnow()`.

**Manual verification (MT-9.AC):**

After wiring:
1. Launch the app — idle icon appears.
2. Switch macOS to dark mode — icon inverts cleanly to white.
3. Trigger "Run now" — syncing icon appears briefly.
4. Simulate an error (disconnect network, trigger sync) — error icon appears.
5. Restart app — correct icon (idle or error) restored from `.phantom_state.json`.

**Test coverage (`tests/test_icon_wiring.py`):**
- `test_init_uses_icon_file` — assert `self.icon` set to `"assets/icon.png"` and `title` is not the emoji.
- `test_set_syncing_true_shows_sync_icon` — assert `self.icon == "assets/icon_syncing.png"`.
- `test_set_syncing_false_after_success_shows_idle` — assert `self.icon == "assets/icon.png"`.
- `test_set_syncing_false_after_error_shows_error` — `_last_sync_failed=True`; assert `self.icon == "assets/icon_error.png"`.
- `test_update_sync_failed_shows_error_icon` — `failed=True`; assert `self.icon == "assets/icon_error.png"`.
- `test_update_sync_success_shows_idle_icon` — `failed=False`; assert `self.icon == "assets/icon.png"`.
- `test_load_state_error_shows_error_icon` — state with `last_sync_failed: true`; assert `self.icon == "assets/icon_error.png"`.

**Dependencies:** H-1 through H-3 complete (icons placed before code runs, but unit tests mock file existence).

---

## Feature-Wide Acceptance Criteria

- **FAC-1**: `uv run python -m pytest tests/ -v` exits 0.
- **FAC-2**: `assets/` directory with all 3 PNGs committed to git.
- **FAC-3**: No emoji icon strings (`⏰`, `⏳`, `⏰❌`) remaining as `self.title` for icon state.
- **FAC-4**: `README.md` icon table accurate.
- **FAC-5**: `build/tests.sh` passes without modification.

---

## Constraints

- Only `app.py` is modified (Python code).
- PNG files are committed to `assets/` (not gitignored).
- Unit tests must mock file I/O — do not require actual PNG content to run.

---

## Non-Goals

- Animated icons.
- `.icns` bundle icon (PyInstaller packaging feature).
- @1x (non-Retina) variants.

---

## Definition of Done

- [ ] H-1 through H-3 complete — 3 PNG files in `assets/`.
- [ ] `app.py` updated — all emoji title assignments replaced with icon path assignments.
- [ ] `tests/test_icon_wiring.py` — 7 cases, all passing.
- [ ] `uv run python -m pytest tests/ -v` exits 0.
- [ ] Manual verification: idle, dark mode, syncing, error, restart icon states all correct.
- [ ] `README.md` icon table accurate.

---

## Parallelization Analysis

Human steps H-1–H-3 must complete before any icon-dependent testing. US-1 code can be written in parallel with H-1–H-3 since unit tests mock the icons.

---

## File Touch List

### Create
- `assets/icon.png` (human)
- `assets/icon_syncing.png` (human)
- `assets/icon_error.png` (human)
- `tests/test_icon_wiring.py`

### Modify
- `app.py`

### Do NOT touch
- `sync_job.py`, `scheduler.py`, `drive_config.py`, `auth.py`, `requirements.txt`
