---
description: Brief me on where this project stands before I start working
---

Read, in this order:

1. `.claude/state/manifest.json`
2. `.claude/state/STATE.md`
3. `.claude/state/BLOCKERS.md`
4. The five most recent entries in `.claude/state/DECISIONS.md`

Then verify the state file against reality rather than trusting it:

```bash
git log --oneline -5
git status --short
cd backend && .venv/bin/python -m pytest tests -q
```

Report in under 20 lines:

- **You are here** — version, phase, what works
- **Blocked on** — each open blocker in one line
- **Next** — the next three tasks from STATE.md
- **Drift** — anything where the state file and the code disagree. Say so explicitly;
  the code wins.

Do not start work. Stop after the briefing.
