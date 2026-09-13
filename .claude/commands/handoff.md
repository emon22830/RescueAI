---
description: Write this session's work back into project state so the next session starts informed
---

Write the state files so that someone returning in six months with no memory of this
session can pick up immediately.

1. Review what changed:
   ```bash
   git status --short
   git diff --stat HEAD
   git log --oneline -10
   ```

2. Rewrite `.claude/state/STATE.md`:
   - the one-paragraph summary of where things stand
   - move finished items into "Done"
   - the **next three tasks**, specific enough to start without thinking
   - the run commands, if they changed

3. Append to `.claude/state/DECISIONS.md` for every non-obvious choice made this session
   — context, decision, consequence. Next id after the current `latest_adr`. Never edit
   an existing entry; supersede it.

4. Update `.claude/state/BLOCKERS.md` — add what is newly blocked, move what was resolved
   into `CHANGELOG.md`.

5. Update `.claude/state/CHANGELOG.md` under the current version if something shipped.

6. Update `.claude/state/manifest.json` — `updated`, `latest_adr`, `open_blockers`, and
   any version or context version that changed.

Then report in three lines what state you wrote. Do not commit unless asked.
