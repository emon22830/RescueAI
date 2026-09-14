# Integration rules — `app/integrations/`

Every file has the same two functions, and a third if it is a **token app** (below).

```python
def collect_evidence(project_id: str, project_name: str) -> list[Evidence]: ...
def execute_action(action: PlannedAction) -> str: ...
```

`PlannedAction.project_id` is what `execute_action` uses to look up which project's
credential to write with — every project can connect a different token.

## Two kinds of credential

This is a multi-tenant SaaS: every project connects its own tools, so where a
credential lives depends on which kind of app it is.

- **Token apps — Slack, Linear, GitHub, Jira, Asana, Trello, Notion.** A user pastes a
  credential into the project's Connections page. It is never stored globally. Add a
  third function:
  ```python
  def verify_token(token: str, **extra) -> dict: ...
  ```
  Called once, by the connect flow, with the raw pasted token — before anything is
  saved. It makes one cheap real call (Slack `auth.test`, a minimal Linear query, a
  GitHub repo read) and either raises with the app's own error message or returns a
  small dict of metadata worth remembering (team name, repo full name). Nothing is
  stored until this succeeds.

  `collect_evidence` and `execute_action` then fetch the decrypted token themselves via
  `app.projects.service.get_integration_credential(project_id, provider)` — a lazy,
  in-function import, to avoid a circular import with `service.py`. A `None` result
  means this project never connected that app: return `[]` from `collect_evidence`,
  raise from `execute_action`.

- **OAuth apps — Gmail, Drive, Calendar.** Still one shared Google OAuth client for the
  whole deployment, read from `app.config.settings` as before. This is a known gap
  (Phase 2 moves them to the same per-project model as the token apps) — see
  `.claude/state/blockers.md`.

## Collecting
- Return `Evidence`, never an app-specific shape. Normalizing here is what lets the
  agents reason across apps.
- `url` is not optional in spirit — it is what makes a finding checkable. Always populate
  it when the API gives you one.
- Fill `timestamp`. The risk agent reasons about sequence: requirements changed *after*
  implementation started.
- Put app-specific extras in `metadata` (issue state, assignee, PR status).
- Never return fabricated data. Unimplemented means `return []`.
- Fetch a bounded amount — a recent window, not the whole workspace.

## Executing
- Return a short human-readable result. It is shown in the UI verbatim.
- Raise on failure; `approve_actions` catches it and records `status = "failed"`.
- Never execute anything the user has not approved.

## Credentials
- OAuth apps (Google): from `app.config.settings` only. A missing one must fail with
  `settings.require(...)`, so the user sees 503 with the variable name instead of a
  stack trace.
- Token apps (the seven above): from `service.get_integration_credential`, never from
  `settings`. A missing one is not an error — `collect_evidence` returns `[]` like any
  other unconnected app.
- **Anything passed as `extra` is stored as metadata and read back to the owner**, so
  no second secret goes there. A site, a repo, a workspace id, a project key are all
  fine. Trello's `key` is the edge case: it identifies the application rather than the
  user, and Trello's own docs ship it client-side — the token beside it is the secret
  half, and that is the one that gets encrypted.

## Adding one

The file is the easy part; a connector also has to be wired into the `Source` literal,
an investigator node, the executor's catalog, the service's token list, the API catalog,
three SQL check constraints and four frontend maps. Use
`.claude/skills/new-integration/SKILL.md`, which lists all of them and names the tests
that fail when one is missed.
