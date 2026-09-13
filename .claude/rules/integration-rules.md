# Integration rules — `app/integrations/`

Every file has the same two functions and nothing else.

```python
def collect_evidence(project_name: str) -> list[Evidence]: ...
def execute_action(action: PlannedAction) -> str: ...
```

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
- From `app.config.settings` only.
- A missing credential must fail with `settings.require(...)`, so the user sees 503 with
  the variable name instead of a stack trace.

## Adding one
Use `.claude/skills/new-integration/SKILL.md`.
