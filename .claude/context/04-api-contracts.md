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
| POST | `/projects/{id}/analyze` | **202** a *queued* `agent_run` — poll `/runs` for the result |
| POST | `/projects/{id}/sync` | **202** a queued `agent_run`, `triggered_by: "sync"` |
| PUT | `/projects/{id}/schedule` | the project, with its new `sync_interval_minutes` |
| GET | `/projects/{id}/findings` | findings from the latest completed run |
| GET | `/projects/{id}/runs` | run history, newest first |
| GET | `/projects/{id}/actions` | actions from the latest completed run |
| POST | `/projects/{id}/actions/approve` | the approved actions, executed, with results |
| GET | `/projects/{id}/actions/types` | what this project can be asked to do, given what it connected |
| POST | `/projects/{id}/actions` | **201** one action written by the user, already executed |
| POST | `/projects/{id}/ask` | an answer drawn only from the latest run's evidence |
| GET | `/projects/{id}/integrations` | connection status for all ten apps on this project |
| POST | `/projects/{id}/integrations/{provider}/connect` | verify a token and store it encrypted |
| DELETE | `/projects/{id}/integrations/{provider}` | **204** forget this project's token |
| GET | `/notifications` | what the agent concluded while you were away, newest first |
| POST | `/notifications/read` | the list again, with those ids marked read |

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
  "sync_interval_minutes": 60,        // null = manual only; the floor is 15
  "last_synced_at": "...",            // null until the scheduler has run it
  "connected": ["slack", "linear"],   // apps this project can reach, for its card
  "summary": { "health": "on_track|watch|at_risk",
               "summary": "two or three sentences from the agent",
               "progress": 40,          // null when the evidence did not measure it
               "blockers": 0, "risks": 0, "findings": 0 } }

// agent_run — one pass of the workflow and the state it concluded with
// `queued` = accepted, not started. /analyze and /sync both return one of these.
{ "id": "uuid", "status": "queued|running|completed|failed",
  "triggered_by": "analyze|sync|schedule",   // schedule = the agent ran itself
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
                  "content": "...", "url": "...", "timestamp": "...",
                  // app-specific extras — issue status, assignee, board, labels.
                  // The readable parts are already folded into `content`.
                  "metadata": {} } ] }

// action — one step of the recovery plan, or one a user took; and where it got to
{ "id": "uuid", "integration": "linear",
  "type": "see GET /actions/types",
  "origin": "agent|user",         // agent = proposed then approved · user = written here
  "description": "what will happen and why it unblocks the finding",
  "target": "PAY-124",            // the issue, the attendees, the recipient
  "reason": "title of the finding this action fixes",
  "params": { "value": "..." },   // the change, the body, the purpose — plus extras
  "status": "pending|approved|executing|completed|failed",
  "result": "what the app said back, or why it failed",
  "approved_at": null, "executed_at": null }

// approve request
{ "action_ids": ["uuid", "uuid"] }

// schedule request — null turns monitoring off; anything under 15 is a 422
{ "sync_interval_minutes": 60 }

// action type — the composer is built from these, never from a hardcoded list.
// The full catalog is executor.ACTION_TYPES; this endpoint filters it to what the
// project has actually connected, so an unconnected app is never offered.
{ "integration": "linear", "type": "create_issue",
  "verb": "add|update|delegate|close|message",   // how the UI groups it
  "label": "Create an issue",
  "target_label": "Issue title",                 // what `target` means here
  "value_label": "What the issue is for" }       // what `params.value` means here

// create-action request — writing it is the approval, so it runs in the request
{ "integration": "slack", "type": "post_message",
  "target": "#payments", "value": "PAY-124 is blocked on the sandbox key.",
  "description": "", "params": {} }

// notification — written by a run, never by a user action. In-app only.
{ "id": "uuid", "project_id": "uuid", "run_id": "uuid",
  "kind": "health_changed|blockers_found|run_failed",
  "severity": "info|warn|danger",
  "title": "SaaS Product Launch is now At risk",
  "body": "the agent's summary, or what failed",
  "read_at": null, "created_at": "..." }

// mark-read request
{ "notification_ids": ["uuid"] }

// ask request / response — the answer never leaves the evidence behind
{ "question": "What is blocking us?" }
{ "question": "...", "answer": "...",       // markdown: bold, code, bullets, one heading
  "answered": true,                   // false = the evidence does not answer it
  "kind": "answer|gap|chat",          // chat = a hello, not a hole in the evidence
  "follow_ups": ["..."],              // up to three the same evidence could answer next
  "evidence": [ { "source": "linear", "type": "issue", "title": "...",
                  "content": "...", "url": "...", "timestamp": "...", "metadata": {} } ] }

// integration status — never a secret, only names and what the app said about itself
{ "id": "slack", "mode": "token",     // "token" = connected here · "oauth" = from .env
  "connected": true,
  "metadata": { "team": "Acme", "bot_user": "rescue-bot" },  // token apps, after verify
  "writes_back": false,               // true for linear, gmail, calendar, slack, github
  "setup_url": "https://api.slack.com/apps",
  "variables": [] }                   // oauth apps only: env vars still empty

// connect request — the credential, plus whatever else that one app needs.
// Everything but `token` is stored as metadata and read back to the owner, so nothing
// secret belongs beside it. Which fields apply to which app is EXTRA_FIELDS on the
// frontend and ConnectIntegrationRequest on the backend.
{ "token": "…",
  "repo": "owner/name",              // github
  "channel_ids": "C01ABC,C02DEF",    // slack, optional
  "site": "acme.atlassian.net",      // jira
  "email": "you@acme.com",           // jira — the account the token was issued for
  "project_key": "PAY",              // jira, optional
  "key": "…",                        // trello — the API key paired with the token
  "workspace": "12345" }             // asana, optional
```

## Errors

| Status | When | Body |
|---|---|---|
| 401 | Missing, invalid or expired token | `{"detail": "Missing bearer token"}` / `"Invalid or expired session"` |
| 422 | Invalid body | Pydantic field errors |
| 400 | A value the service refused | `{"detail": "The shortest schedule is every 15 minutes"}` |
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
| `/app/projects/:id/connections` | that project's ten apps | yes |

Signing in lands on `/app`. Anything unmatched redirects to `/`.
