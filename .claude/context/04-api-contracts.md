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
| POST | `/projects/{id}/sync` | the completed `agent_run`, `triggered_by: "sync"` |
| GET | `/projects/{id}/findings` | findings from the latest completed run |
| GET | `/projects/{id}/runs` | run history, newest first |
| GET | `/projects/{id}/actions` | actions from the latest completed run |
| POST | `/projects/{id}/actions/approve` | the approved actions, executed, with results |

Add an endpoint only when a feature needs it.

`analyze` and `sync` run the same investigation: collect from every connected app,
analyze, write the project state. `sync` exists because re-collecting is the action a
user means to take on a project they already analyzed; `triggered_by` keeps the two
apart in the run history. Findings and actions always come from the latest completed
run, so a sync replaces what is on screen rather than appending to it.

An app with no credentials contributes no evidence and says so in the run's `activity`.
Nothing in the backend fabricates a finding to fill the gap.

Approving is the only thing that sends anything to an external app. `approve` takes the
ids the user picked, moves those actions from `pending` to `approved`, and executes them
inside the same request — no queue, no worker, no polling. Each one is written to the
database as `executing` before its integration is called and as `completed` or `failed`
after, so the status a client reads is always the truth. Ids that are not `pending` are
skipped, which makes a double-approve a no-op rather than a second write to Linear. A
failing step does not stop the rest of the plan; its error is stored as its `result`.

## Shapes

```jsonc
// project — summary is the latest completed run's project state, stored not recomputed
{ "id": "uuid", "name": "...", "goal": "...", "created_at": "...",
  "summary": { "health": "on_track|watch|at_risk",
               "summary": "two or three sentences from the agent",
               "progress": 40,          // null when the evidence did not measure it
               "blockers": 0, "risks": 0, "findings": 0 } }

// agent_run — one pass of the workflow and the state it concluded with
{ "id": "uuid", "status": "running|completed|failed",
  "triggered_by": "analyze|sync",
  "started_at": "...", "completed_at": "...",
  "evidence_count": 6, "finding_count": 1,
  "health": "at_risk", "summary": "...", "progress": 40,
  "activity": [ { "agent": "communication", "status": "ok|failed",
                  "detail": "slack: 4 items", "evidence_count": 4, "at": "..." } ],
  "error": null }

// finding
{ "id": "uuid", "title": "...", "severity": "low|medium|high|critical",
  "confidence": 0.91, "description": "...",
  "evidence": [ { "source": "slack", "type": "message", "title": "...",
                  "content": "...", "url": "...", "timestamp": "..." } ] }

// action — one step of the recovery plan and where it has got to
{ "id": "uuid", "integration": "linear",
  "type": "update_issue|assign_task|update_due_date|create_event|send_email",
  "description": "what will happen and why it unblocks the finding",
  "target": "PAY-124",            // the issue, the attendees, the recipient
  "reason": "title of the finding this action fixes",
  "params": { "value": "..." },   // the change, the body, the purpose — plus extras
  "status": "pending|approved|executing|completed|failed",
  "result": "what the app said back, or why it failed",
  "approved_at": null, "executed_at": null }

// approve request
{ "action_ids": ["uuid", "uuid"] }
```

## Errors

| Status | When | Body |
|---|---|---|
| 422 | Invalid body | Pydantic field errors |
| 404 | Unknown project | `{"detail": "No project with id …"}` — every `/projects/{id}/…` path |
| 503 | Missing env vars | `{"detail": "Missing environment variable(s): …"}` |
| 502 | Supabase failed | `{"detail": "Database error: …"}` |

All four are raised centrally in `app/main.py`. Do not catch them per route.

## Frontend contract

Every call goes through `frontend/src/lib/api.ts`. Components never call `fetch`.
Types live in `features/*/types.ts` and must match the shapes above.
