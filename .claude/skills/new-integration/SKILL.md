---
name: new-integration
description: Implement one external app integration for AI Project Rescue — Slack, Gmail, Google Drive, Linear, GitHub or Google Calendar. Use when wiring a real API to collect evidence or execute an approved action.
---

# Adding an integration

Six of these get built. They are all the same shape, so build them the same way.

## 1. Check what the agent expects

```python
# app/agents/state.py
class Evidence(BaseModel):
    source: Source          # slack | gmail | drive | linear | github | calendar
    type: str               # message | email | issue | pull_request | document | event
    title: str
    content: str
    url: str | None
    timestamp: datetime | None
    metadata: dict
```

`url` and `timestamp` are what make a finding checkable and orderable. Treat them as
required in practice.

## 2. Get a credential and declare it

Add the variable to `app/config.py` and `backend/.env.example` (empty value), then put
the real one in `backend/.env`. Never commit it.

## 3. Read the live API docs

Do not write a client from memory — endpoint shapes and auth headers drift. Fetch the
current docs for the search or list call you need.

Prefer `httpx` against the REST or GraphQL endpoint over a heavy SDK. Add a dependency
to `requirements.txt` only if your code imports it.

## 4. Implement `collect_evidence`

```python
def collect_evidence(project_name: str) -> list[Evidence]:
    settings.require("linear_api_key")
    # 1. query the API for items matching project_name, bounded to a recent window
    # 2. map each item to Evidence
    # 3. return the list
```

- Search by `project_name` — that is the only handle the agent has.
- Bound the result. A recent window, not the whole workspace.
- Map to `Evidence` **inside this file**. Nothing app-specific escapes.
- On an API error, let it raise. Do not swallow it and return `[]` — a silent empty list
  is indistinguishable from "nothing found" and will waste an hour.

## 5. Implement `execute_action` if the app is a write target

Only Linear, Calendar and Gmail are. The others raise `NotImplementedError`.

```python
def execute_action(action: PlannedAction) -> str:
    if action.action == "update_issue":
        target = action.params["target"]   # e.g. "PAY-124"
        value = action.params["value"]
        # ... call the API ...
        return f"Updated {target}: {value}"
    raise NotImplementedError(f"Linear action not implemented: {action.action}")
```

The returned string is shown to the user verbatim. Make it specific.

## 6. Verify against the real app

```bash
cd backend
.venv/bin/python -c "
from app.integrations import linear
for item in linear.collect_evidence('SaaS Product Launch'):
    print(item.source, '|', item.title, '|', item.url)
"
```

You are checking three things: items come back, each has a working URL, and the content
is enough for a model to reason about. Then run the full workflow and confirm the risk
agent produces a finding that cites this source.

## 7. Update state

- `.claude/state/STATE.md` — move it from "not done" to "done"
- `.claude/state/CHANGELOG.md` — add the entry
- `.claude/state/ROADMAP.md` — tick the phase item
- An ADR only if you made a non-obvious choice

## Order

Slack → Linear → GitHub → Calendar → Gmail → Drive. The first three are what the demo
cannot survive without.
