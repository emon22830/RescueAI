# Backend rules

## Structure
- `api/` parses and delegates. No business logic, no database calls.
- `projects/service.py` holds business logic and owns every Supabase call.
- Never add a repository class, a manager, a factory, or a `utils.py`.
- Name functions for behaviour: `analyze_project`, `collect_evidence`, `approve_actions`.

## Types
- Type-hint every function signature.
- Pydantic models for every request and response body.
- `list[str]`, `dict`, `str | None` — modern syntax, no `Optional` or `List`.

## Errors
- Raise; do not return error dicts.
- The handlers in `main.py` cover config, auth, not-found, database and validation.
  Add a handler there rather than try/except in a route.
- Config errors must name the missing variable. `settings.require("supabase_url", ...)`.

## Auth
- Every route that touches a project depends on `app.auth.get_current_user` and passes
  `user.id` into `projects/service.py` as the owner to check against.
- The backend calls Supabase with the service key, which bypasses row-level security —
  so ownership is an application-code check in `service.py`, never assumed from the URL.
- An id that exists but belongs to someone else raises the same `ProjectNotFound` as an
  id that doesn't exist. Never let a 403 confirm that a project id is real.

## Database
- Only `projects/service.py` calls `get_db()`.
- Findings and actions are always scoped to the latest completed run.
- Batch inserts — one call per table, not one per row.
- No N+1. If you are querying inside a loop over projects, restructure.

## Secrets
- Everything through `app/config.py`. Never `os.environ` elsewhere, never a literal.

## Tests
- A new endpoint needs a test through `TestClient`.
- Use the `client` fixture; it swaps Supabase for `tests/fake_db.py`.
- Test behaviour a user would notice, not internals.
