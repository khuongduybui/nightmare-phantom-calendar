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
3. Spec: 36×36 px, black monochrome line art, transparent background, single stroke weight, no fill, no gradients, no shadows.
4. Place the new PNG in `assets/` and update `app.py` to reference it in the correct state handler.
5. Update `README.md` icon table with the new state.

**Owner:** Implementer, Feature-Review

---

## Rule: no-scheduler-in-npc-0000

**When:** Reviewing NPC-0000 scope only.
**Action:** `app.py` must not import or reference `scheduler.py`. Scheduler wiring belongs to a future feature.
**Owner:** QA, Story-Review
