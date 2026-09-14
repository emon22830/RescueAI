# Where the project is

**Updated:** 2026-09-14 · **Version:** 0.6.0 · **Phase:** 4 of 4 — Proven against a live workspace

## In one paragraph

RescueAI does the whole job it was designed for. It reads ten apps, reasons over the
evidence, names blockers with the evidence attached, proposes a recovery plan, and —
once a human approves — carries that plan out in nine of the ten, across 31 action
types covering create, update, delegate, close and message. It no longer waits to be
asked: a project can re-analyse itself on a schedule, and the owner is told in the app
when the verdict changes. A user can also act directly from the dashboard without
waiting for the agent to propose anything. Whichever tracker a team runs — Linear,
Jira, Asana or Trello — is covered, which is what makes it usable outside a startup.

**It has now run for real.** Migrations 0002–0005 are applied to the live Supabase
project, and a full analysis has completed end to end against a live workspace: 10
real GitHub commits collected with working URLs, the project state written by the risk
agent in its own words, and Ask answering from that evidence with citations. 223 tests
back it, and the suite is hermetic.

Two bugs were found by that first live run, and by nothing else: the recovery planner
sent a schema the Gemini Developer API refuses outright, and a transient provider 503
threw away a whole investigation after the evidence had been collected. Both are fixed,
both now have tests. What is still unproven is narrow: **no write action has been
executed against a real workspace**, because that needs a token with write scope on
something safe to write to.

## Done

- Backend: FastAPI, config, Supabase client, project service, **23 endpoints**
- Auth: Supabase Auth, per-project ownership checked in `service.py`, never from the URL
- Per-project encrypted credentials for Slack/Linear/GitHub, per-project Google consent
- LangGraph workflow: supervisor → 3 parallel investigators → risk → recovery
- Every run persists evidence, findings, actions, activity, health, summary, progress
- **Ten integrations collect; nine execute, across 31 action types.** The whole manager
  vocabulary — add, update, delegate, close, message — in whichever app the team uses.
  Trackers: Linear, **Jira**, **Asana**, **Trello**. Chat and mail: Slack, Gmail. Code:
  GitHub. Specs and dates: Drive, **Notion**, Calendar. Drive is the one app that only
  ever collects ([[adr-0021]])
- **Four investigators, not three.** `delivery` reads every tracker and `engineering`
  keeps GitHub alone — what a team built and what its plan says are different questions,
  and the distance between them is the finding ([[adr-0020]])
- **One catalog, `executor.ACTION_TYPES`, is the contract** between the planner, the API
  and the UI. The recovery prompt is generated from it and the composer is served it, so
  a type cannot exist in one place and not another — a test proves it ([[adr-0018]])
- **A user can act without the agent proposing it.** `POST /projects/{id}/actions` takes
  one action straight from the dashboard, through the same row, states and guard as an
  approved plan step; `origin` records who wrote it ([[adr-0019]])
- **An analysis is accepted, not awaited.** `POST /analyze` and `/sync` return **202**
  with a `queued` run; the work happens behind the request and the run row is the
  handle. A failure is recorded on the run instead of raised as a 500 ([[adr-0015]])
- **Continuous monitoring.** `PUT /projects/{id}/schedule` sets a per-project interval;
  `app/scheduler.py` is one in-process asyncio loop that runs what is due ([[adr-0016]])
- **Notifications.** A scheduled run that changes a project's health, or fails, writes a
  notification. In-app only — a verdict is never posted into someone's Slack
  unapproved ([[adr-0017]]). `GET /notifications`, `POST /notifications/read`
- Frontend: the project page follows a run to completion instead of blocking on the
  request, a Monitoring card turns the schedule on and off, a "Take an action" composer
  acts on any connected app, and a bell in the app shell surfaces what the agent
  concluded while nobody was watching
- **The live Supabase project exists and works.** `backend/.env` is filled in; 4
  projects, 4 runs and 3 connected integrations (GitHub, Google) are in the real
  database. The old "no credentials" blocker is gone.
- 203 backend tests passing, and hermetic — the suite no longer reaches the live
  Supabase project ([[adr-0022]]); `npm run build` and `npm run lint` clean

## Not done

- **None of the three migrations has been run against the live database.** `0002`
  (scheduling and notifications), `0003` (dashboard actions) and `0004` (the four new
  connectors) are all outstanding. Until `0002`, `PUT /schedule` answers 502 and no
  notification can be written; until `0003`, `POST /actions` answers 502 because
  `run_id` is still `not null`; until `0004`, connecting Jira, Notion, Asana or Trello
  — or storing any evidence from them — violates a check constraint. Analysis through
  the original six still works.
- Slack and Linear are not connected on any live project, so the two richest evidence
  sources have never been collected from for real
- No finding has ever been produced from live evidence — `findings` has 0 rows
- The demo scenario still does not exist in the real workspaces (blocker 2)
- No write action has been executed against a live workspace. The request shapes match
  the current API docs and are pinned by tests down to the JSON body, but nothing has
  round-tripped a real token.

## Next three tasks

1. **Execute one write against a real workspace** — the last unproven path. Slack
   `post_message` is the sharpest test: it is the only write with a lookup in front of
   it (`resolve_channel`), and it needs `chat:write`, which collection does not. Connect
   Slack on a throwaway channel, take the action from the dashboard composer, and read
   what comes back.
2. **Get a second app onto one project**, so the risk agent is judged on *cross-app*
   evidence. Today's live run had GitHub alone, and a finding is only worth reading when
   it connects two sources — with one app the honest answer was 0 findings, which is
   correct but proves only half the prompt.
3. **Take one action from the dashboard against a real workspace** — a Slack
   `post_message` is the sharpest test, because it is the only write with a lookup in
   front of it (`resolve_channel` turns `#payments` into a channel id) and it needs the
   `chat:write` scope, which is *not* in the scope list collection asks for. Then try a
   Linear `create_issue`, the only other write that has to resolve something it was not
   given (`resolve_team`).

## How to run it

```bash
# backend  → http://localhost:8000   (the scheduler starts with it)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 --host ::
cd backend && .venv/bin/python -m pytest tests -q

# frontend → http://localhost:5173
cd frontend && npm run dev && npm run build
```

The scheduler is in-process: monitoring only runs while the backend is running. Set
`SCHEDULER_ENABLED=false` on any second instance, or both will pick up the same project.

If `.venv` is missing: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
