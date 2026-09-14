# RescueAI

**Projects don't fail silently — they fail in ten different apps at once.**

The status in Jira says *In Progress*. The Slack thread says the API contract changed
three weeks ago. The spec in Notion still describes the old one. The client email asking
about the launch date is unanswered. Nobody is lying; nobody is looking at every place
at the same time.

RescueAI is an agent that does exactly that. It pulls evidence out of the tools a team
already uses, cross-references it against the project goal, names the blockers and risks
with the receipts attached, drafts a recovery plan, and — only after a human ticks the
box — executes that plan back into those same tools.

```
Collect evidence → Understand state → Detect blockers → Recovery plan
      ↑                                                      ↓
   Sync again  ←  Execute actions  ←  Human approval  ←──────┘
```

▶️ **Presentation demo:** https://youtu.be/sbWLUt8JJik

**Jump to:** [What it does](#what-it-does) · [The apps it connects](#the-apps-it-connects) ·
[How it works](#how-it-works) · [Why you can trust it](#why-you-can-trust-it) ·
[Run it locally](#run-it-locally) · [Reference](#reference)

---

## What it does

**The problem.** Project status is a report someone writes by hand, from memory, once a
week. It is always a little out of date and always a little optimistic. The signals that
a project is in trouble are real and already written down — they are just scattered
across ten tools, and no single one of them can see the contradiction between them.

| Without it | With it |
|---|---|
| Status is self-reported and stale | Status is derived from what the tools actually contain |
| "I think we're blocked on payments" | "PAY-124 is overdue, the Slack thread on Aug 28 says the provider contract changed, and spec v3 still describes the old one" — with links to all three |
| Risks surface at the deadline | Risks surface the moment the evidence contradicts itself |
| A status meeting produces a to-do list | An analysis produces a plan that executes into your tools in one click |
| An AI summary you have to fact-check | Every sentence carries the evidence it came from |

**Who it is for.** A project lead, a founder, or a delivery manager running work across
more tools than anyone can read daily. One person, several projects, no new process —
the team keeps working the way it already works, and the agent reads the exhaust.

**The rule that makes a finding worth reading:** it must connect evidence from **more
than one source**. Anyone can read a single task list; the value is in the contradiction
between them.

### What it produces

| | |
|---|---|
| **Evidence** | A normalized fact from one app — a Slack message, a Jira issue, a PR, a doc, a calendar event. Always carries `source`, `type`, `title`, `content`, `url`, `timestamp` and app-specific `metadata`. |
| **Finding** | A blocker or risk, with a severity (`low` → `critical`), a confidence score, and the exact evidence items that support it. |
| **Project state** | Health (`on_track` / `watch` / `at_risk`), a written summary, and progress where the evidence measures it. |
| **Recovery plan** | Concrete actions, each tied to a finding, none executed without approval. |
| **Activity log** | What each agent did to each app on this run, including what contributed nothing and why. |

### What it can do to your tools

**Thirty-one action types across nine apps** — the whole vocabulary a delivery lead
needs, in whichever app the team actually uses:

| | Slack | Linear | Jira | Asana | Trello | GitHub | Notion | Gmail | Calendar |
|---|---|---|---|---|---|---|---|---|---|
| **Create** | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| **Update** | — | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ |
| **Delegate** | — | ✓ | ✓ | ✓ | — | ✓ | — | — | — |
| **Close** | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| **Message** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |

Drive is the one app that only ever collects. The list lives in one place —
`executor.ACTION_TYPES` — which the recovery prompt is generated from and the dashboard
composer is served, so a step the agent can propose is always a step that can actually
run.

### Three things beyond "analyze and report"

**Ask.** A free-text question about the project (`POST /projects/{id}/ask`), answered
only from evidence the last run actually collected, with the same citations. If the
evidence cannot answer it, it says so instead of guessing.

**It runs itself.** A project can re-analyse on its own schedule — hourly, every six
hours, or daily. `/analyze` and `/sync` return a *queued* run immediately and the
investigation happens behind the request, so a slow workspace never times out the
browser. When a scheduled run changes a project's verdict, or fails, the owner is told
in the app. Nothing here bypasses approval: a scheduled run still only *proposes*.

**You can act directly.** A "Take an action" composer on the project page does any of
the above without waiting for the agent to propose it. Writing it is the approval, so it
runs immediately — through the same row, the same states and the same guard, and
recorded as yours rather than the agent's.

---

## The apps it connects

Each app is **one file** in [backend/app/integrations/](backend/app/integrations/) with
the same two functions — `collect_evidence()` and `execute_action()`, plus
`verify_token()` where a credential is pasted. Every one normalizes into the same
`Evidence` shape, which is what lets the agents reason across apps at all.

| App | Connects with | Collects | Can execute |
|---|---|---|---|
| **Slack** | bot token | messages from the last 30 days in the project's channels | post a message |
| **Gmail** | Google consent | mail from the last 60 days matching the project | send an email |
| **GitHub** | fine-grained token + `owner/repo` | commits, pull requests and issues, last 30 days | open · comment · assign · close |
| **Linear** | API key | the project and its issues — state, assignee, due date | create · update · assign · re-date · comment · close |
| **Jira** | API token + site + account email | issues matching the project, last 30 days | create · assign · re-date · comment · close |
| **Asana** | personal access token | tasks in the matching Asana project | create · assign · re-date · comment · complete |
| **Trello** | user token + API key | cards mentioning the project, with their board | create · re-date · comment · archive |
| **Drive** | Google consent | matching files, Docs and Sheets exported to text | *read-only* |
| **Notion** | integration token | pages naming the project, and their text | create a page · comment |
| **Calendar** | Google consent | events from a week ago to 90 days ahead | book · reschedule · cancel |

Connect as few or as many as you like — the agent works with what it can reach, and says
in the activity log what it could not. **A team runs one tracker, not four**: Linear,
Jira, Asana and Trello are alternatives, not a checklist.

Gmail, Drive and Calendar are three APIs behind **one** Google consent — connecting any
of them connects all three. Every request is bounded to a recent window rather than the
whole workspace, and every call carries a timeout.

---

## How it works

One LangGraph workflow lives in [backend/app/agents/](backend/app/agents/):

```
                         supervisor
                              │
        ┌───────────────┬─────┴─────┬───────────────┐
        ▼               ▼           ▼               ▼
  communication    engineering   delivery      requirements
   Slack             GitHub       Linear          Drive
   Gmail                          Jira            Notion
                                  Asana           Calendar
                                  Trello
        └───────────────┴─────┬─────┴───────────────┘
                              ▼
                            risk        cross-references everything → findings
                              ▼
                          recovery      findings → a concrete plan
                              ▼
                       (human approves)
                              ▼
                          executor      writes to the connected app. No LLM.
```

**1. The investigators run in parallel.** `evidence` and `agent_activity` are
`Annotated[list, operator.add]` in [state.py](backend/app/agents/state.py), so all four
branches append to the same lists without overwriting each other. `risk` waits for all
of them before it runs.

**2. `engineering` and `delivery` are deliberately separate.** What a team *built* and
what its plan *says* are different questions, and the distance between them is most of
what this product exists to find — so they are collected by different agents and appear
as different lines in the activity log.

**3. Investigators do not reason.** They collect and normalize. Only `risk` and
`recovery` call the model, and only through [ai/llm.py](backend/app/ai/llm.py) — the
single file in the codebase that talks to an LLM. Answers come back validated against a
Pydantic schema, so no agent ever parses loose JSON.

**4. Nothing is executed by an agent.** `recovery` only *proposes*. The plan is written
to the `actions` table as `pending`, and the executor runs only the rows a human
approved.

### Platform

| Layer | Choice |
|---|---|
| LLM | **Gemini** (`gemini-3.8-flash`) via the `google-genai` SDK, structured output |
| Agent orchestration | **LangGraph** — parallel fan-out, one shared state |
| Backend | **FastAPI** + Pydantic (Python 3.12+) |
| Database & auth | **Supabase** (Postgres + Supabase Auth) |
| Frontend | **React 19** · Vite · TypeScript · Tailwind CSS 4 |
| HTTP to external apps | **`httpx`** against documented REST/GraphQL endpoints — no vendor SDKs |
| Scheduling | one in-process `asyncio` loop ([scheduler.py](backend/app/scheduler.py)) — no broker, no worker |

### Data model

Seven tables, created by [backend/schema.sql](backend/schema.sql): `projects`,
`integrations`, `agent_runs`, `evidence`, `findings`, `actions`, `notifications`.

`schema.sql` builds a **fresh** database. A database created from an earlier version
needs every file in [backend/migrations/](backend/migrations/) run in order —
`create table if not exists` does not add a column to a table that already exists, and
it does not widen a check constraint either.

---

## Why you can trust it

An agent that reports on a project is only useful if you can check it. Reliability here
is not a promise in a prompt — it is enforced in code, in eight places.

**Findings cite evidence by index, not by paraphrase.** The `risk` agent is handed
**numbered** evidence and must return `evidence_indexes`, resolved back to the real
stored objects in [risk.py](backend/app/agents/risk.py) — bounds-checked before use. The
model never restates a Slack message in its own words, so it cannot soften it, sharpen
it, or invent one that does not exist.

**Nothing external is fabricated — ever.** An integration with no credential returns
`[]` and writes a line in the activity log saying so. There is no demo fixture anywhere
in the source. If the dashboard shows a finding, something real produced it.

**"No findings" is always a legal answer.** Every system prompt states explicitly what
an empty answer looks like. A model that is required to find a problem will invent one.
The workflow also short-circuits before spending a token: no evidence → no findings,
no findings → no plan.

**One broken app does not lose the other nine.** `supervisor.investigate` runs each app
inside its own `try`, and a failure becomes a visible line of activity
(`gmail: HTTPStatusError: 429`) while the investigation carries on. A partial setup still
produces real findings from the apps that are wired up.

**Failures are recorded, not swallowed.** The run row is written before the work starts,
so a crash leaves a trace instead of nothing. Exception handlers in
[main.py](backend/app/main.py) map what actually goes wrong to honest status codes — and
no route writes its own `try/except`:

| Failure | Response |
|---|---|
| Missing environment variable | **503**, naming the exact variable |
| Bad, missing or expired token | **401** |
| Unknown project, or someone else's | **404** |
| A value the service refused | **400**, with the reason |
| Model returned nothing usable | **502**, with the model's finish reason |
| Database error | **502**, with the Postgres message |

**The executor has no intelligence in it.**
[executor.py](backend/app/agents/executor.py) maps an action to an integration and calls
it. No LLM, no improvisation. It re-checks the database status at the moment of
execution and raises `NotApproved` on anything that is not `approved` — so the approval
gate holds even if a caller gets it wrong.

**A re-sync replaces, it never piles up.** Findings, actions and the health summary are
always scoped to the **latest completed run**. Syncing shows what is true now, not an
accumulating history. Past runs stay readable in the run history.

**It is tested where it matters.** **203 backend tests** run the real FastAPI app
through `TestClient` against an in-memory stand-in for Supabase — the full analyze →
findings → approve → execute path, the 401/404 ownership rules, the evidence-citation
mapping, the wire format of every write action, and a guard asserting that an
unconnected integration returns `[]` and never reaches the network. The suite is
hermetic: it cannot touch a real database.

```
203 passed in 0.39s
```

---

## Security and multi-tenancy

Full detail in [backend/app/auth/README.md](backend/app/auth/README.md).

- **We do not store users.** Supabase Auth owns sign-up, sign-in, password hashing and
  sessions. There is no users table of ours and no login endpoint on this server.
- **Every request is identified.** The frontend attaches the session's `access_token` as
  `Authorization: Bearer …`; `get_current_user` turns it into a user id.
- **Ownership is checked in application code**, on every service call, because the
  backend uses the Supabase service key and therefore bypasses row-level security by
  design.
- **404, never 403.** A project that exists but belongs to someone else answers exactly
  like one that never existed. A 403 would confirm that a project id is real.
- **Connected credentials are encrypted at rest.** Each project connects its *own*
  tokens; they are verified live against the real API, then stored in the `integrations`
  table encrypted with Fernet under `CREDENTIAL_ENCRYPTION_KEY`. No API response ever
  returns a credential value.
- **Nothing secret is stored as metadata.** A site, a repo, a workspace id is readable
  back to the owner; a second secret is not. Trello's API key is the one exception, and
  only because it identifies the application rather than the user.
- **The Google OAuth `state` is signed** with a 10-minute TTL, so a forged, altered or
  stale redirect is rejected as 401.
- `.env` is gitignored and never committed. The repo is public — check before every push.

---

## Run it locally

**Prerequisites:** Python 3.12+, Node 20+, a free Supabase project, a Gemini API key.

Deploying instead of running locally — env values, redirect URIs, CORS — is
[DEPLOYMENT.md](DEPLOYMENT.md).

### 1 — Clone

```bash
git clone https://github.com/emon22830/RescueAI.git
cd RescueAI
```

### 2 — Create the database

1. Create a project at <https://supabase.com>.
2. Open **SQL Editor**, paste all of [backend/schema.sql](backend/schema.sql), run it
   once. *Already had a database from an earlier version?* Run every file in
   [backend/migrations/](backend/migrations/) in order instead.
3. From **Project Settings → API**, copy the **Project URL**, the **anon** key and the
   **service_role** key. The service key is a server secret — it never goes in the
   frontend.

### 3 — Get a Gemini API key

From <https://aistudio.google.com/apikey>.

### 4 — Configure the backend

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, and generate the key
that encrypts every credential a project connects:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

No app's credential goes in `.env` — each project connects its own from the app.
`.env.example` documents what each one wants and what scopes it needs.

### 5 — Run the backend

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 --host ::
```

<http://localhost:8000/docs> for interactive API docs. The scheduler starts with it.

### 6 — Configure and run the frontend

```bash
cd frontend
npm install
cp .env.example .env     # VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm run dev
```

`VITE_API_URL` stays empty in dev: Vite proxies to `127.0.0.1:8000`, so there is no CORS
setup to do.

### 7 — Create a project

Give it a **name** and a **goal**. The goal is what every finding is judged against, so
write the real one: *"Ship the v2 payments launch to customers by Oct 31."*

### 8 — Connect the apps

On the project's **Connections** page. Each credential is verified against the live API
before it is stored, so a wrong paste fails immediately with the app's own error rather
than silently later.

| App | What to paste | Where to get it |
|---|---|---|
| **Slack** | bot token (`xoxb-…`) | <https://api.slack.com/apps> — read scopes `channels:history`, `groups:history`, `channels:read`, `groups:read`, `users:read`; add **`chat:write`** to post. **Invite the bot to the channels.** |
| **Linear** | personal API key | Settings → API → Personal API keys |
| **Jira** | API token + site + account email | <https://id.atlassian.com/manage-profile/security/api-tokens> — site is `acme.atlassian.net` |
| **Asana** | personal access token | <https://app.asana.com/0/my-apps> — the workspace is detected for you |
| **Trello** | user token **and** its API key | <https://trello.com/power-ups/admin> |
| **GitHub** | fine-grained token + `owner/repo` | <https://github.com/settings/personal-access-tokens> — read that repo, plus Issues r/w to act |
| **Notion** | internal integration token | <https://www.notion.so/my-integrations> — then share each page with it |
| **Google** | click **Connect** → consent screen | see below — one consent covers Gmail, Drive and Calendar |

**Google OAuth, one-time setup for the deployment:** create a **Web application** OAuth
client at <https://console.cloud.google.com/apis/credentials>, enable the Gmail, Drive
and Calendar APIs, request scopes `gmail.readonly`, `gmail.send`, `drive.readonly` and
`calendar.events`, and register this exact redirect URI:

```
http://localhost:8000/integrations/google/callback
```

Then add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_CALENDAR_ID=primary` to
`backend/.env`. These identify the *application*; each project's own grant is stored
encrypted against that project.

### 9 — Run the first analysis

Click **Analyze**. The workflow fans out, collects, reasons, and writes back a health
state, findings and a proposed plan. The activity log shows what each app contributed.

### 10 — Approve a plan

Review the recovery plan, tick the actions you agree with, click **Approve & execute**.
Only those rows run; each records the integration's own result. Nothing else was ever
going to reach your workspace.

---

## Using the app

| Screen | What it is for |
|---|---|
| **Dashboard** | Every project with its current health, finding counts and last run |
| **Project** | The latest analysis: summary, findings with evidence, recovery plan, run history, activity log — plus the action composer and the monitoring schedule |
| **Ask** | A question about this project, answered only from collected evidence, with citations |
| **Connections** | Connect, verify and disconnect this project's apps |

Day to day: **Sync** before a status meeting, read the findings, approve the plan. Or
turn monitoring on and let it tell you when the verdict changes.

---

## Reference

### API

Every route except `/health` and the OAuth callback requires `Authorization: Bearer`.
Interactive docs: <http://localhost:8000/docs> (the **Authorize** button takes a real
session token).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness — `{"status":"ok"}` |
| GET | `/auth/me` | Who the bearer token belongs to |
| POST | `/projects` | Create a project (name + goal) |
| GET | `/projects` | List your projects with their health summaries |
| GET | `/projects/{id}` | One project plus its health summary |
| DELETE | `/projects/{id}` | Delete the project and everything under it |
| PUT | `/projects/{id}/schedule` | Turn continuous monitoring on or off |
| POST | `/projects/{id}/analyze` | Queue an analysis — **202**, poll `/runs` for the result |
| POST | `/projects/{id}/sync` | The same work again, replacing the current state |
| GET | `/projects/{id}/findings` | Blockers and risks, with their evidence |
| GET | `/projects/{id}/runs` | Analysis history, including failed and queued runs |
| GET | `/projects/{id}/actions` | The recovery plan, and anything you did yourself |
| GET | `/projects/{id}/actions/types` | What this project can be asked to do |
| POST | `/projects/{id}/actions` | Take one action directly — **201**, already executed |
| POST | `/projects/{id}/actions/approve` | Approve the chosen actions and execute them |
| POST | `/projects/{id}/ask` | Ask a question, answered from this project's evidence |
| GET | `/projects/{id}/integrations` | Every app and whether this project can reach it |
| POST | `/projects/{id}/integrations/{provider}/connect` | Verify and store a credential |
| DELETE | `/projects/{id}/integrations/{provider}` | Disconnect an app |
| GET | `/projects/{id}/integrations/google/authorize` | Start the Google consent flow |
| GET | `/integrations/google/callback` | Where Google returns — signed `state`, no bearer |
| GET | `/notifications` | What the agent concluded while you were away |
| POST | `/notifications/read` | Mark notifications read |

### Project layout

```
backend/app/
  api/            HTTP endpoints — projects, analysis, actions, integrations, ask, notifications
  auth/           who is calling, and how connected credentials are kept safe
  projects/       business logic and the only code that queries Supabase
  agents/         the LangGraph workflow, its nodes, and the action catalog
  integrations/   one file per external app
  ai/llm.py       the only place that talks to an LLM
  scheduler.py    the loop that re-analyses projects on their own schedule
  db/supabase.py  database client
  config.py       every environment variable, in one place
  main.py         app, CORS, routers, lifespan, error handlers
backend/schema.sql  the seven tables, for a fresh database
backend/migrations/ schema changes for a database that already exists
backend/tests/      203 tests against the real app and a fake database

frontend/src/
  pages/          Landing · Login · Dashboard · Project · Connections
  features/       projects · intelligence · integrations · notifications · marketing
  components/     ui/ presentational pieces · layout/ shell
  lib/api.ts      typed client for every endpoint above — the only place that fetches
  lib/auth.tsx    session context, route guard, Supabase client
```

### Tests and checks

```bash
# backend — 203 tests, no network, no real database
cd backend && .venv/bin/python -m pytest tests -q

# frontend — type-checks, builds, lints
cd frontend && npm run build
cd frontend && npm run lint
```

The backend suite swaps Supabase for `tests/fake_db.py` automatically, and tests
behaviour a user would notice rather than internals.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| **503** with a variable name | That variable is missing from `backend/.env`. Add it and restart. |
| **401** on every call | Not signed in, or the session expired. Sign in again. |
| **404** on a project you believe exists | Wrong account — a project you do not own answers 404 on purpose. |
| **502 "did not return a valid …"** | The model answered with nothing usable. Retry; check `GEMINI_API_KEY` and quota. |
| **502 "Database error"** | `schema.sql` has not been run, or was run against a different project. |
| **502 on turning monitoring on**, or a log line about `last_synced_at` | The database predates continuous monitoring. Run `migrations/0002_scheduling_and_notifications.sql`. |
| **502 on taking an action from the dashboard** | `actions.run_id` is still `not null`. Run `migrations/0003_actions_from_the_dashboard.sql`. |
| **502 mentioning a check constraint on `source` or `integration`** | The database predates Jira/Notion/Asana/Trello. Run `migrations/0004_more_connectors.sql`. |
| **Slack action fails with `missing_scope`** | The bot token needs `chat:write`, which reading does not require. Add it and reinstall the app. |
| **Slack returns 0 items** | The bot is not in the channel. Invite it. |
| **Jira collects nothing** | The token belongs to a different site, or the account cannot see the project. Jira's search endpoint changed in 2025 — a forked older `jira.py` must call `/rest/api/3/search/jql`. |
| **Notion collects nothing** | Notion only returns pages the integration has been *shared with*. Open the page → ••• → Connections → add it. |
| **Asana collects nothing** | It finds the Asana *project* by name first. Rename it to match, or connect the right workspace. |
| **Linear/Jira `create_issue` asks for a team or project** | A multi-team workspace with no match by name. Set `params.team` (Linear) or `params.project` (Jira) to one of the keys it listed. |
| **Monitoring is on but nothing runs** | The scheduler is in-process: the backend has to be running. Check `SCHEDULER_ENABLED` and the startup log. |
| **Analysis finds nothing** | No app is connected, or the connected ones hold nothing about this project. Read the run's activity log — it names each app and what it returned. |
| Browser shows raw JSON on a project page | Stale dev server — restart `npm run dev`. |
| Frontend throws "Missing VITE_SUPABASE_URL" | `frontend/.env` is missing. Copy `.env.example` and fill it in. |

---

## Status

**Working end to end:** authentication, projects, per-project encrypted credentials for
ten apps, the full LangGraph workflow, persistence of every run with its evidence,
findings, actions and activity, the approval gate, the executor, Ask, continuous
monitoring, direct actions from the dashboard, and the React UI over all of it.
203 backend tests pass; the frontend builds and lints clean.

**Not yet proven.** No analysis has run against a live workspace, and no write has
touched a real one. Every request shape is pinned by a test down to the JSON body and
checked against current API docs — but that proves the right request is sent, not that
the API accepts it.

**Next**

- Move Google from one deployment-wide OAuth client to fully per-project consent
- A shared work queue, so more than one backend instance can run schedules safely
  (today the scheduler is one in-process loop — see [scheduler.py](backend/app/scheduler.py))
- Digest notifications by email, for people who do not keep the app open
