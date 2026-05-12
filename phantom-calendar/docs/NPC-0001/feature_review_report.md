---
phase: Feature-Review
date: 2026-05-12
status: PASS
spec_hash: 46a663679694
---

# Feature Review Report — NPC-0001 (Decision Engine)

## Definition of Done Check

| Item | Status |
|------|--------|
| `drive_config.py` created: `CONFIG_FILE_ID`, `DEFAULT_CONFIG_YAML`, `read_config()`, `bootstrap_config()`, `write_config()`, `parse_config()` (12 keys) | ✅ |
| `calendar_reader.py` created: `LOCAL_TZ`, `get_tomorrow_range()`, `get_msi_time_blocks()`, `get_personal_events()` | ✅ |
| `compute.py` created: `match_block_to_meeting()`, `compute_alarm()` (7-key result) | ✅ |
| `config.yaml` at project root with canonical default YAML | ✅ |
| `requirements.txt` updated: `pyyaml==6.0.2` | ✅ |
| `tests/test_drive_config.py` — 12 cases, all passing | ✅ |
| `tests/test_calendar_reader.py` — 8 cases, all passing | ✅ |
| `tests/test_compute.py` — 12 cases, all passing | ✅ |
| `uv run python -m pytest tests/ -v` exits 0 (37/37) | ✅ |
| `README.md` updated with new files in Project Structure table | ✅ |
| `build/manual_tests.md` updated with MT-1001.H2 | ✅ |
| No `credentials.json` / `token.json` in staged files | ✅ |
| No `datetime.utcnow()` in new code | ✅ |
| `build/tests.sh` runs without modification | ✅ |

---

## Code Review

### `drive_config.py`

- **CONFIG_FILE_ID** — env-configurable via `PHANTOM_CONFIG_FILE_ID`; hardcoded default is the known Drive file ID. ✓
- **DEFAULT_CONFIG_YAML** — loaded from `config.yaml` at import time (single source of truth). ✓
- **read_config()** — validates with `yaml.safe_load()`; falls back to `bootstrap_config()` on any error or empty result. ✓
- **bootstrap_config()** — writes default, then renames file to `config.yaml` only if not already `.yaml`. Conditional rename prevents redundant API calls. ✓
- **write_config()** — uses `MediaIoBaseUpload` with `text/plain` mimetype. ✓
- **parse_config()** — all 12 keys present, sane defaults for every key, recurring meetings normalised with guaranteed `notes` field. ✓
- **No hardcoded values** — all defaults are overridable from YAML; design principle satisfied. ✓

### `calendar_reader.py`

- **get_tomorrow_range()** — uses `date.today() + timedelta(days=1)` localised to `LOCAL_TZ`; no UTC dependency. ✓
- **get_msi_time_blocks()** — returns `start`/`end` only (no title leak); all-day events silently skipped; sorted ascending. ✓
- **get_personal_events()** — returns `title`/`start`/`end`; all-day events skipped; sorted ascending. ✓
- **datetime.fromisoformat()** throughout; no deprecated APIs. ✓
- Both functions accept optional `calendar_id` parameter for testability. ✓

### `compute.py`

- **match_block_to_meeting()** — 5-minute tolerance (`abs(delta.total_seconds()) <= 300`); parses meeting times as `%H:%M` (consistent with `config.yaml` 24h format). ✓
- **compute_alarm()** — correctly returns all 7 spec-required keys. Alarm events excluded by `'Alarm' in title`. No-meetings case handled. ✓
- **is_baseline** — uses `config['baseline_event_title']` and `config['baseline_event_time']` (no hardcoded strings). ✓
- **Pure computation** — no network calls, no imports from `auth`/`drive_config`/`calendar_reader`. ✓
- `_is_baseline_alarm()` extracted as private helper — clean separation. ✓

### `config.yaml`

- Canonical YAML structure committed. Serves as both repo reference and `DEFAULT_CONFIG_YAML` source. ✓
- Contains current real recurring meetings (AERSS Standup, Pod 8 Daily Sync) with correct prep times. ✓

---

## Policy Compliance

| Policy | Status |
|--------|--------|
| No `datetime.utcnow()` | ✅ |
| No hardcoded configurable values | ✅ |
| `auth.py` not modified | ✅ |
| `credentials.json` / `token.json` excluded from git | ✅ |
| Python 3.14 compatible | ✅ |
| Fish shell / uv conventions in docs | ✅ |
| `app.py`, `scheduler.py`, `popup.py`, `calendar_writer.py`, `sync_job.py` not created | ✅ |

---

## Rune Compliance (`docs/runes/phantom-calendar.md`)

| Rule | Status |
|------|--------|
| `update-build-tests-sh` — pytest auto-discovers; `tests.sh` unchanged | ✅ |
| `update-manual-tests-md` — MT-1001.H2 added for H-2 (MSI freeBusyReader) | ✅ |
| `update-readme` — Project Structure table and test count updated | ✅ |
| `no-credentials-in-git` — confirmed absent | ✅ |
| `python-version-compatibility` — no removed APIs used | ✅ |
| `venv-and-uv-conventions` — all new docs use `uv run` / `uv pip` / fish activation | ✅ |

---

## Test Summary

| Suite | Count | Result |
|-------|-------|--------|
| `test_auth.py` (NPC-0000) | 4 | ✅ PASS |
| `test_main.py` (NPC-0000) | 1 | ✅ PASS |
| `test_drive_config.py` (NPC-0001/US-1) | 12 | ✅ PASS |
| `test_calendar_reader.py` (NPC-0001/US-2) | 8 | ✅ PASS |
| `test_compute.py` (NPC-0001/US-3) | 12 | ✅ PASS |
| **Total** | **37** | ✅ **37/37** |

---

## Findings

None. All acceptance criteria, policy rules, and rune rules satisfied.

---

## Accepted Findings and Justifications

N/A — no findings to accept.

---

## Merge Recommendation

**APPROVED** — NPC-0001 is ready to merge to `main`.
