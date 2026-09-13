---
doc: api-contracts
version: 1
updated: 2026-09-14
status: active
---

# API

Base URL `http://localhost:8000`. The frontend proxies `/projects` and `/health` to it
via `vite.config.ts`, so the browser calls same-origin paths. The proxy only forwards
requests that do not accept HTML — the app has a `/app/projects/:id` route as well as a
`/projects` API path, and without that a page reload would return raw JSON.

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` — the only unauthenticated path |
| GET | `/auth/me` | the caller's `{id, email}`, or 401 |
| POST | `/projects` | **201** the project + summary |
| GET | `/projects` | list, newest first, each with summary |
| GET | `/projects/{id}` | the project + summary |
| POST | `/projects/{id}/analyze` | the completed `agent_run` |
| POST | `/projects/{id}/sync` | the completed `agent_run`, `triggered_by: "sync"` |
| GET | `/projects/{id}/findings` | findings from the latest completed run |
| GET | `/projects/{id}/runs` | run history, newest first |
| GET | `/projects/{id}/actions` | actions from the latest completed run |
| POST | `/projects/{id}/actions/approve` | the approved actions, executed, with results |
| POST | `/projects/{id}/ask` | an answer drawn only from the latest run's evidence |
| GET | `/projects/{id}/integrations` | connection status for all six apps on this project |
| POST | `/projects/{id}/integrations/{provider}/connect` | verify a token and store it encrypted |
| DELETE | `/projects/{id}/integrations/{provider}` | **204** forget this project's token |

Add an endpoint only when a feature needs it.

**Every path except `/health` requires `Authorization: Bearer <supabase access token>`.**
Sign-in happens in the browser against Supabase directly, so there is no login endpoint
here and there should not be one. The backend verifies the token, resolves it to a user
id, and checks that id against `owner_id` on every row it returns — a project that is
not yours is **404, never 403**, so a status code can never confirm that an id is real.
See `backend/app/auth/README.md`.

`analyze` and `sync` run the same investigation: collect from every connected app,
analyze, write the project state. `sync` exists because re-collecting is the action a
user means to take on a project they already analyzed; `triggered_by` keeps the two
apart in the run history. Findings and actions always come from the latest completed
run, so a sync replaces what is on screen rather than appending to it.

An app with no credentials contributes no evidence and says so in the run's `activity`.
Nothing in the backend fabricates a finding to fill the gap.

`ask` is not a chatbot bolted on the side — it is one more view onto the state the
workflow already built. The answer may only use evidence from the latest completed run,
it cites that evidence by index the way a finding does, and a question the evidence
cannot answer comes back with `answered: false` and what is missing, never a guess. A
project that has **never run** is refused without an LLM call at all; a run that
collected **nothing** still gets one, under a prompt that forbids every claim about the
project — because "hi" and "what can you do?" deserve a reply, not an evidence warning.

The answer is markdown (bold, inline code, bullets, one heading level) and carries
`kind` — `answer` grounded in evidence, `gap` the evidence cannot fill, `chat` a
greeting or a question about the agent — plus up to three `follow_ups` the same evidence
could answer next. Only `gap` is flagged in the UI. A question may be up to 2000
characters, so a user can paste context in. Nothing is stored: the thread is a way of
reading a run, not a record, so it lives in the browser for the session and no table
grows.

Integrations belong to a project, not to the deployment: one project's Slack token is
not another's. Slack, Linear and GitHub are `token` apps — the user pastes a credential,
the backend verifies it against the real API before storing it encrypted, so a bad token
fails at the moment it is entered rather than as a mysteriously empty investigation.
Gmail, Drive and Calendar are still `oauth`: one Google client in `backend/.env` for the
whole deployment, so their status is reflected configuration and they have no connect
endpoint yet. Nothing on this path ever returns a credential value — only variable
names, a boolean, and what the app said about itself when the token was verified.

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
  "connected": ["slack", "linear"],   // apps this project can reach, for its card
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

// ask request / response — the answer never leaves the evidence behind
{ "question": "What is blocking us?" }
{ "question": "...", "answer": "...",
  "answered": true,                   // false = the evidence does not answer it
  "evidence": [ { "source": "linear", "type": "issue", "title": "...",
                  "content": "...", "url": "...", "timestamp": "..." } ] }

// integration status — never a secret, only names and what the app said about itself
{ "id": "slack", "mode": "token",     // "token" = connected here · "oauth" = from .env
  "connected": true,
  "metadata": { "team": "Acme", "bot_user": "rescue-bot" },  // token apps, after verify
  "writes_back": false,               // true for linear, gmail, calendar
  "setup_url": "https://api.slack.com/apps",
  "variables": [] }                   // oauth apps only: env vars still empty

// connect request — repo is github only, channel_ids slack only and optional
{ "token": "…", "repo": "owner/name", "channel_ids": "C01ABC,C02DEF" }
```

## Errors

| Status | When | Body |
|---|---|---|
| 401 | Missing, invalid or expired token | `{"detail": "Missing bearer token"}` / `"Invalid or expired session"` |
| 422 | Invalid body | Pydantic field errors |
| 404 | Unknown project | `{"detail": "No project with id …"}` — every `/projects/{id}/…` path |
| 503 | Missing env vars | `{"detail": "Missing environment variable(s): …"}` |
| 502 | Supabase failed | `{"detail": "Database error: …"}` |

All of these are raised centrally in `app/main.py`. Do not catch them per route.

## Frontend contract

Every call goes through `frontend/src/lib/api.ts`, which attaches the current Supabase
session token as `Authorization: Bearer …` on every request. Components never call
`fetch`. Types live in `features/*/types.ts` and must match the shapes above.

### Routes

| Path | What | Session |
|---|---|---|
| `/` | public landing page — makes no API call at all | no |
| `/login` | Google sign-in | no |
| `/app` | the dashboard | yes |
| `/app/projects/:id` | one project: state, findings, plan, activity | yes |
| `/app/projects/:id/connections` | that project's six apps | yes |

Signing in lands on `/app`. Anything unmatched redirects to `/`.
