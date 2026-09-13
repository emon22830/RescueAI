---
doc: api-contracts
version: 1
updated: 2026-09-14
status: active
---

# API

Base URL `http://localhost:8000`. The frontend proxies `/projects` and `/health` to it
via `vite.config.ts`, so the browser calls same-origin paths.

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| POST | `/projects` | **201** the project + summary |
| GET | `/projects` | list, newest first, each with summary |
| GET | `/projects/{id}` | the project + summary |
| POST | `/projects/{id}/analyze` | the completed `agent_run` |
| POST | `/projects/{id}/sync` | same as analyze |
| GET | `/projects/{id}/findings` | findings from the latest completed run |
| GET | `/projects/{id}/runs` | run history, newest first |
| GET | `/projects/{id}/actions` | actions from the latest completed run |
| POST | `/projects/{id}/actions/approve` | the executed actions with results |

Add an endpoint only when a feature needs it.

## Shapes

```jsonc
// project
{ "id": "uuid", "name": "...", "goal": "...", "created_at": "...",
  "summary": { "health": "on_track|watch|at_risk",
               "blockers": 0, "risks": 0, "findings": 0 } }

// finding
{ "id": "uuid", "title": "...", "severity": "low|medium|high|critical",
  "confidence": 0.91, "description": "...",
  "evidence": [ { "source": "slack", "type": "message", "title": "...",
                  "content": "...", "url": "...", "timestamp": "..." } ] }

// action
{ "id": "uuid", "integration": "linear", "action": "update_issue",
  "description": "...", "params": { "target": "PAY-124", "value": "..." },
  "status": "pending|executed|failed", "result": null }

// approve request
{ "action_ids": ["uuid", "uuid"] }
```

## Errors

| Status | When | Body |
|---|---|---|
| 422 | Invalid body | Pydantic field errors |
| 404 | Unknown project | `{"detail": "No project with id …"}` |
| 503 | Missing env vars | `{"detail": "Missing environment variable(s): …"}` |
| 502 | Supabase failed | `{"detail": "Database error: …"}` |

All four are raised centrally in `app/main.py`. Do not catch them per route.

## Frontend contract

Every call goes through `frontend/src/lib/api.ts`. Components never call `fetch`.
Types live in `features/*/types.ts` and must match the shapes above.
