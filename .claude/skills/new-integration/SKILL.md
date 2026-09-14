---
name: new-integration
description: Implement one external app integration for RescueAI — Slack, Gmail, Drive, Linear, Jira, Asana, Trello, GitHub, Notion or Calendar. Use when wiring a real API to collect evidence or execute an approved action.
---

# Adding an integration

Ten of these exist. They are all the same shape, so build the next one the same way.

An integration is **one file** in `app/integrations/`, plus wiring in eight other places.
The file is the easy part. The wiring is what gets forgotten, so it has its own
checklist below and two tests that fail if you skip it.

## 1. The two functions every app has, and the third token apps have

```python
def collect_evidence(project_id: str, project_name: str) -> list[Evidence]: ...
def execute_action(action: PlannedAction) -> str: ...
def verify_token(token: str, **extra) -> dict: ...   # token apps only
```

`project_id` is how you find *this project's* credential. There is no global token:
this is multi-tenant, and every project connects its own.

```python
from app.projects import service          # lazy, inside the function —
                                          # a module-level import is circular
credential = service.get_integration_credential(project_id, "jira")
if credential is None:
    logger.warning("Jira skipped: project %s has not connected Jira", project_id)
    return []                             # never fabricate, never raise
```

`verify_token` is called once by the connect flow with the raw pasted credential,
**before anything is stored**. Make one cheap real call (`auth.test`, `/myself`,
`/users/me`), raise with the app's own error message, or return a small dict of
metadata worth remembering. Nothing is saved until it succeeds.

## 2. Read the live API docs. Do not write a client from memory

Endpoint shapes drift, and the drift is silent. Jira removed `/rest/api/3/search`
entirely in 2025 — code written from memory against it collects nothing and reports
no error worth reading. Fetch the current docs for the call you need, every time.

Prefer `httpx` against the REST or GraphQL endpoint over a vendor SDK. Add to
`requirements.txt` only if your code imports it.

## 3. Collect

- Search by `project_name` — with `project_id` for the credential, that is the only
  handle the agent has.
- **Bound it.** A recent window and a cap, not the whole workspace.
- Map to `Evidence` **inside this file**. Nothing app-specific escapes.
- `url` and `timestamp` are what make a finding checkable and orderable. Treat them as
  required in practice.
- App-specific extras go in `metadata` (status, assignee, board, labels).
- On an API error, let it raise. The investigator node catches it and writes it to the
  run's activity log, which is where a user can see it. A swallowed error returning `[]`
  is indistinguishable from "nothing found" and will waste an hour.

## 4. Execute, if the app can be written to

Nine of the ten can. Dispatch on `action.type`, and **raise `NotImplementedError` for a
type you do not handle** — a test depends on that being the signal.

```python
if action.type == "comment_issue":
    return comment_on_issue(action.target, _required(body, "comment_issue"), *args)
raise NotImplementedError(f"Jira action not implemented: {action.type}")
```

`target` is what the step acts on; `params["value"]` is the change, body or message.
The returned string is shown to the user verbatim — make it name what happened and
link to it. A failure should say what to type instead:

```python
raise JiraError(f"{key}: no transition called '{name}'. Available: {available}")
```

## 5. Wire it into the other eight places

A file nobody imports collects nothing. In order:

| Where | What |
|---|---|
| `app/agents/state.py` | add to the `Source` literal |
| `app/agents/<node>.py` | add to the investigator that asks its kind of question |
| `app/agents/executor.py` | `INTEGRATIONS`, and an `ActionType` per write action |
| `app/projects/service.py` | `TOKEN_INTEGRATIONS`, if it is a token app |
| `app/api/integrations.py` | `CATALOG`, `VERIFY_ERRORS`, and any `ConnectIntegrationRequest` field |
| `backend/migrations/` | a migration widening the three check constraints |
| `frontend/.../types.ts` + `SourceIcon.tsx` | the `Source` union, a glyph, a label |
| `frontend/.../providers.ts` | `PROVIDERS`, `SOURCE_ORDER`, `CREDENTIAL_LABEL`, `EXTRA_FIELDS` |

TypeScript catches the frontend half for you — `Record<Source, …>` will not compile
until every map has the new key. The backend half is caught by tests:

- `test_every_catalogued_action_type_is_actually_dispatchable` — a type in
  `ACTION_TYPES` that `execute_action` does not handle
- `test_this_file_covers_every_app_the_workflow_investigates` — an app the graph reads
  that the unconnected-contract test never checks
- `test_every_token_app_is_connectable_from_the_frontend` — a `verify_token` the
  service does not know about, so nobody can ever connect it

**Nothing secret goes in `extra`.** It is stored as metadata and read back to the owner.
A site, a repo, a workspace id — fine. A second secret belongs in the encrypted half.

## 6. Verify against the real app

```bash
cd backend
.venv/bin/python -c "
from app.integrations import jira
for item in jira.collect_evidence('<a real project id>', 'SaaS Product Launch'):
    print(item.source, '|', item.title, '|', item.url)
"
```

Three things: items come back, each URL opens the real thing, and the content is enough
for a model to reason about. Then run one `POST /projects/{id}/analyze` and confirm the
risk agent produces a finding that cites this source.

## 7. Update state

- `.claude/state/STATE.md` — move it from "not done" to "done"
- `.claude/state/CHANGELOG.md` — add the entry
- `.claude/state/ROADMAP.md` — tick the item
- An ADR only if you made a non-obvious choice

## Order

The trackers first — they are where the plan lives, and a gap between the plan and the
work is what this product exists to find. Then chat, then docs, then calendars.
