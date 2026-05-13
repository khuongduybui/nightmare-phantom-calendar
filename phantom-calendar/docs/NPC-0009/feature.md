# What the feature is

Custom icon design for the Phantom Calendar menu bar app. Replaces the emoji text title (`⏰`, `⏳`, `⏰❌`) with proper monochrome PNG template images that adapt to macOS light/dark mode and look native in the menu bar.

# Why we need it

Emoji characters in the menu bar look out of place and do not follow macOS Human Interface Guidelines. Template images (black monochrome on transparent background) are the correct approach — macOS automatically inverts them for dark mode and tints them when the menu bar is active.

# Icon States Required

Three icons are needed, one per sync state:

| File | State | Triggered by |
|---|---|---|
| `assets/icon.png` | Normal / idle | Default |
| `assets/icon_syncing.png` | Sync in progress | `set_syncing(True)` |
| `assets/icon_error.png` | Last sync failed | `update_sync_state(failed=True)` |

# Image Generation Prompts (for Gemini or similar)

## Prompt 1 — Normal state (`assets/icon.png`)

```
Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.

Design: A simple alarm clock silhouette — circular clock face with two small bells on top and a single bell-hammer in the center bottom. The clock hands point to approximately 9 o'clock. Minimal detail, single stroke weight, no gradients, no shadows.
```

## Prompt 2 — Syncing state (`assets/icon_syncing.png`)

```
Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.

Design: The same alarm clock silhouette as the base icon, but with two curved arrows forming a circular refresh/sync symbol overlaid in the bottom-right quadrant of the clock face. The refresh arrows should be small (roughly 1/3 the clock size) and clearly convey "in progress" or "syncing". Single stroke weight, no gradients, no shadows.
```

## Prompt 3 — Error state (`assets/icon_error.png`)

```
Create a macOS menu bar icon. Style: monochrome black line art on transparent background, 36×36 pixels, no fill, clean vector aesthetic, suitable as a template image.

Design: The same alarm clock silhouette as the base icon, but with a small exclamation mark (!) inside a circle or triangle badge in the bottom-right corner of the icon. The badge should be clearly readable at small size. Single stroke weight, no gradients, no shadows.
```

# Acceptance Criteria (testable)

**AC1 — Assets directory**
`phantom-calendar/assets/` exists and contains `icon.png`, `icon_syncing.png`, `icon_error.png`.

**AC2 — Icon used on startup**
`app.py` passes `icon="assets/icon.png"` to `rumps.App.__init__()` and removes `title="⏰"`.

**AC3 — Icon swapped during sync**
`set_syncing(True)` sets `self.icon = "assets/icon_syncing.png"` and `set_syncing(False)` restores the appropriate idle or error icon.

**AC4 — Error icon shown on failure**
`update_sync_state(failed=True)` sets `self.icon = "assets/icon_error.png"`.

**AC5 — State restored on startup**
`_load_state()` sets the correct icon based on `last_sync_failed` from the persisted state (NPC-0008).

# System Constraints

- Images must be PNG with transparency, 36×36 pixels (@2x / Retina)
- macOS treats images as template images when provided to rumps — automatic dark mode support
- `assets/` directory committed to git (unlike credential files)
- `app.py` is the only Python file modified

# Non-goals

- Animated icons (not supported by rumps)
- `.icns` bundle icon (belongs to PyInstaller packaging feature)
- @1x variants (Retina is standard)

# Implementation Notes

After placing icons in `assets/`:

```python
# In PhantomCalendarApp.__init__():
super().__init__(name="Phantom Calendar", icon="assets/icon.png", quit_button="Quit")
# Remove: title="⏰"

# In set_syncing():
self.icon = "assets/icon_syncing.png" if syncing else (
    "assets/icon_error.png" if self._last_sync_failed else "assets/icon.png"
)

# In update_sync_state():
self.icon = "assets/icon_error.png" if failed else "assets/icon.png"

# In _load_state():
self.icon = "assets/icon_error.png" if self._last_sync_failed else "assets/icon.png"
```
