# RescueAI

**Projects don't fail silently — they fail in six different apps at once.**

The status in Linear says *In Progress*. The Slack thread says the API contract changed
three weeks ago. The spec in Drive still describes the old one. The client email asking
about the launch date is unanswered. Nobody is lying; nobody is looking at all six places
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

---

## Demo

▶️ **Presentation demo:** _<!-- paste the YouTube link here -->_

---

## Contents

1. [Why it is useful](#1--why-it-is-useful)
2. [Why it can be trusted — reliability](#2--why-it-can-be-trusted--reliability)
3. [What it produces](#3--what-it-produces)
4. [How it works](#4--how-it-works)
5. [Integrations](#5--integrations)
6. [Security and multi-tenancy](#6--security-and-multi-tenancy)
7. [API reference](#7--api-reference)
8. [Project layout](#8--project-layout)
9. [Set it up, step by step](#9--set-it-up-step-by-step)
10. [Using the app](#10--using-the-app)
11. [Tests and checks](#11--tests-and-checks)
12. [Troubleshooting](#12--troubleshooting)
13. [Current status and roadmap](#13--current-status-and-roadmap)

---

## 1 · Why it is useful

**The problem.** Project status is a report someone writes by hand, from memory, once a
week. It is always a little bit out of date and always a little bit optimistic. The
signals that a project is in trouble are real and already written down — they are just
scattered across Slack, Gmail, Drive, Linear, GitHub and Calendar, and no single one of
those tools can see the contradiction between them.

**What RescueAI changes.**

| Without it | With it |
|---|---|
| Status is self-reported and stale | Status is derived from what the tools actually contain, on demand |
| "I think we're blocked on payments" | "PAY-124 is overdue, the Slack thread on Aug 28 says the provider contract changed, and spec v3 in Drive still describes the old one" — with links to all three |
| Risks surface at the deadline | Risks surface the moment the evidence contradicts itself |
| A status meeting produces a to-do list | An analysis produces a plan that can be executed into Linear, Calendar and Gmail in one click |
| An AI summary you have to fact-check | Every sentence carries the evidence it came from |

**Who it is for.** A project lead, a founder, or a delivery manager running work across
more tools than anyone can read daily. One person, several projects, no new process —
the team keeps working the way it already works, and the agent reads the exhaust.

**Concretely, it answers:**

- Where is this project really, right now?
- What is blocking it, and what is the proof?
- What changed since last week that nobody has acted on?
- What should be done next, and can you do it for me?

Plus **Ask** — a free-text question about the project (`POST /projects/{id}/ask`),
answered only from evidence the last run actually collected, with the same citations. If
the evidence cannot answer it, it says so instead of guessing.

**The rule that makes a finding worth reading:** it must connect evidence from **more
than one source**. Anyone can read a single task list; the value is in the contradiction
between them.

---

## 2 · Why it can be trusted — reliability

An agent that reports on a project is only useful if you can check it. Reliability here
is not a promise in a prompt — it is enforced in code, in eight places.

### 2.1 Findings cite evidence by index, not by paraphrase

The `risk` agent is handed **numbered** evidence and must return `evidence_indexes`.
Those indexes are resolved back to the real stored objects in
[risk.py](backend/app/agents/risk.py) — and the index is bounds-checked before it is
used. The model never restates a Slack message in its own words, so it cannot
soften it, sharpen it, or invent one that does not exist. Every finding in the UI opens
to the actual messages, issues and documents behind it, each with its source URL.

### 2.2 Nothing external is fabricated — ever

An integration with no credential returns `[]` and writes a line in the run's activity
log saying so. It never returns sample data, and there is no demo fixture anywhere in
the source. If the dashboard shows a finding, something real produced it.

### 2.3 "No findings" is always a legal answer

Every system prompt states explicitly what an empty answer looks like. A model that is
required to find a problem will invent one. The workflow also short-circuits before
spending a token: **no evidence → no findings**, **no findings → no plan**.

### 2.4 One broken app does not lose the other five

`supervisor.investigate` runs each app inside its own `try`, and a failure becomes a
visible line of activity (`gmail: HTTPStatusError: 429`) while the investigation carries
on with everything else. A partial setup still produces real findings from the apps that
are wired up — and you can see exactly which ones contributed.

### 2.5 Failures are recorded, not swallowed

The run row is written as `running` **before** the work starts, so a crash leaves a
trace instead of nothing; a failure updates it to `status = "failed"` with the real error
text. Five exception handlers in [main.py](backend/app/main.py) map the five things that
actually go wrong to honest status codes — and no route writes its own `try/except`:

| Failure | Response |
|---|---|
| Missing environment variable | **503**, naming the exact variable |
| Bad, missing or expired token | **401** |
| Unknown project, or someone else's | **404** |
| Model returned nothing usable | **502**, with the model's finish reason |
| Database error | **502**, with the Postgres message |

### 2.6 The executor has no intelligence in it

[executor.py](backend/app/agents/executor.py) maps an action to an integration and calls
it. No LLM, no improvisation. It re-checks the database status at the moment of
execution and raises `NotApproved` on anything that is not `approved` — so the approval
gate holds even if a caller gets it wrong. Each action records the integration's own
result line, or `failed` with the reason.

### 2.7 A re-sync replaces, it never piles up

Findings, actions and the health summary are always scoped to the **latest completed
run**. Syncing a project shows you what is true now, not an accumulating history of
everything that was ever wrong. Past runs remain readable in the run history.

### 2.8 It is tested where it matters

**114 backend tests** run the real FastAPI app through `TestClient` against an in-memory
stand-in for Supabase — the full analyze → findings → approve → execute path, the
401/404 ownership rules, the evidence-citation mapping, and a guard asserting that an
unconnected integration returns `[]` and never reaches the network.

```
114 passed in 0.83s
```

---

## 3 · What it produces

| | |
|---|---|
| **Evidence** | A normalized fact from one app — a Slack message, a Linear issue, a PR, a doc, a calendar event. Always carries `source`, `type`, `title`, `content`, `url`, `timestamp` and app-specific `metadata`. |
| **Finding** | A blocker or risk, with a severity (`low` → `critical`), a confidence score, and the exact evidence items that support it. |
| **Project state** | Health (`on_track` / `watch` / `at_risk`), a written summary, and progress where the evidence measures it. |
| **Recovery plan** | 4–5 concrete actions (`update_issue`, `create_event`, `send_email`) — each tied to a finding, none executed without approval. |
| **Activity log** | What each agent did to each app on this run, including what contributed nothing and why. |

---

## 4 · How it works

One LangGraph workflow lives in [backend/app/agents/](backend/app/agents/):

```
                    supervisor
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  communication     engineering      requirements
   Slack + Gmail   GitHub + Linear   Drive + Calendar
        └────────────────┼────────────────┘
                         ▼
                       risk          cross-references everything → findings
                         ▼
                     recovery        findings → a concrete plan
                         ▼
                  (human approves)
                         ▼
                     executor        writes to Linear / Calendar / Gmail
```

**1. The investigators run in parallel.** `evidence` and `agent_activity` are
`Annotated[list, operator.add]` in [state.py](backend/app/agents/state.py), so all three
branches append to the same lists without overwriting each other. `risk` waits for all
three before it runs.

**2. Investigators do not reason.** They collect and normalize. Only `risk` and
`recovery` call the model, and only through [ai/llm.py](backend/app/ai/llm.py) —
the single file in the codebase that talks to an LLM. Answers come back validated
against a Pydantic schema, so no agent ever parses loose JSON.

**3. Nothing is executed by an agent.** `recovery` only *proposes*. The plan is written
to the `actions` table as `pending`, and the executor runs only the rows a human
approved through the UI.

### Platform

| Layer | Choice |
|---|---|
| LLM | **Gemini** (`gemini-3.8-flash`) via the `google-genai` SDK, structured output |
| Agent orchestration | **LangGraph** — parallel fan-out, one shared state |
| Backend | **FastAPI** + Pydantic (Python 3.12+) |
| Database & auth | **Supabase** (Postgres + Supabase Auth) |
| Frontend | **React 19** · Vite · TypeScript · Tailwind CSS 4 |
| HTTP to external apps | **`httpx`** against documented REST/GraphQL endpoints — no vendor SDKs |

### Data model

Six tables, created by [backend/schema.sql](backend/schema.sql): `projects`,
`integrations`, `agent_runs`, `evidence`, `findings`, `actions`.

---

## 5 · Integrations

Each app is **one file** in [backend/app/integrations/](backend/app/integrations/) with
exactly two functions — `collect_evidence()` and `execute_action()` — and every one
normalizes into the same `Evidence` shape, which is what lets the agents reason across
apps at all.

| App | Connects via | Collects | Executes |
|---|---|---|---|
| **Slack** | pasted bot token | messages from the last 30 days in the project's channels | — |
| **Linear** | pasted API key | the project and its issues — state, assignee, due date | `update_issue` · `assign_task` · `update_due_date` |
| **GitHub** | pasted fine-grained token | commits, pull requests and issues from the last 30 days | — |
| **Gmail** | Google OAuth | mail from the last 60 days matching the project | `send_email` |
| **Google Drive** | Google OAuth | matching files, with Docs and Sheets exported to text | — |
| **Google Calendar** | Google OAuth | events from a week ago to 90 days ahead | `create_event` |

Gmail, Drive and Calendar are three APIs behind **one** Google consent — connecting any
of them connects all three. Every request is bounded to a recent window rather than the
whole workspace, and every call carries a timeout.

---

## 6 · Security and multi-tenancy

Full detail in [backend/app/auth/README.md](backend/app/auth/README.md).

- **We do not store users.** Supabase Auth owns sign-up, sign-in, password hashing and
  sessions. There is no users table of ours and no login endpoint on this server.
- **Every request is identified.** The frontend attaches the session's `access_token` as
  `Authorization: Bearer …` to every call; `get_current_user` turns it into a user id.
- **Ownership is checked in application code**, on every service call, because the
  backend uses the Supabase service key and therefore bypasses row-level security by
  design.
- **404, never 403.** A project that exists but belongs to someone else answers exactly
  like one that never existed. A 403 would confirm that a project id is real.
- **Connected credentials are encrypted at rest.** Each project connects its *own* Slack,
  Linear and GitHub tokens; they are verified live against the real API, then stored in
  the `integrations` table encrypted with Fernet under `CREDENTIAL_ENCRYPTION_KEY`.
  No API response ever returns a credential value.
- **The Google OAuth `state` is signed** with a 10-minute TTL, so a forged, altered or
  stale redirect is rejected as 401.
- `.env` is gitignored and never committed. The repo is public — check before every push.

---

## 7 · API reference

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
| POST | `/projects/{id}/analyze` | Run the agent workflow |
| POST | `/projects/{id}/sync` | Run it again and replace the current state |
| GET | `/projects/{id}/findings` | Blockers and risks, with their evidence |
| GET | `/projects/{id}/runs` | Analysis history, including failed runs |
| GET | `/projects/{id}/actions` | The recovery plan and what has been executed |
| POST | `/projects/{id}/actions/approve` | Approve the chosen actions and execute them |
| POST | `/projects/{id}/ask` | Ask a question, answered from this project's evidence |
| GET | `/projects/{id}/integrations` | Every app and whether this project can reach it |
| POST | `/projects/{id}/integrations/{provider}/connect` | Verify and store a token |
| DELETE | `/projects/{id}/integrations/{provider}` | Disconnect an app |
| GET | `/projects/{id}/integrations/google/authorize` | Start the Google consent flow |
| GET | `/integrations/google/callback` | Where Google returns — signed `state`, no bearer |

---

## 8 · Project layout

```
backend/app/
  api/            HTTP endpoints — projects, analysis, actions, integrations, ask
  auth/           who is calling, and how connected credentials are kept safe
  projects/       business logic and the only code that queries Supabase
  agents/         the LangGraph workflow and its nodes
  integrations/   one file per external app: collect_evidence + execute_action
  ai/llm.py       the only place that talks to an LLM
  db/supabase.py  database client
  config.py       every environment variable, in one place
  main.py         app, CORS, routers, error handlers
backend/schema.sql  the six tables
backend/tests/      114 tests against the real app and a fake database

frontend/src/
  pages/          Landing · Login · Dashboard · Project · Connections
  features/       projects · intelligence (findings, plan, ask) · integrations · marketing
  components/     ui/ presentational pieces · layout/ shell
  lib/api.ts      typed client for every endpoint above — the only place that fetches
  lib/auth.tsx    session context, route guard, Supabase client
```

---

## 9 · Set it up, step by step

**Prerequisites:** Python 3.12+, Node 20+, a free Supabase project, a Gemini API key.

### Step 1 — Clone

```bash
git clone https://github.com/emon22830/RescueAI.git
cd RescueAI
```

### Step 2 — Create the database

1. Create a project at <https://supabase.com>.
2. Open **SQL Editor**, paste all of [backend/schema.sql](backend/schema.sql), run it once.
   It creates `projects`, `integrations`, `agent_runs`, `evidence`, `findings`, `actions`.
3. From **Project Settings → API**, copy the **Project URL**, the **anon** key and the
   **service_role** key. The service key is a server secret — it never goes in the frontend.

### Step 3 — Get a Gemini API key

Create one at <https://aistudio.google.com/apikey>.

### Step 4 — Configure the backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `backend/.env`:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...            # service_role, server only
GEMINI_API_KEY=AIza...
LLM_MODEL=gemini-3.8-flash
CREDENTIAL_ENCRYPTION_KEY=...          # generate it, see below
CORS_ORIGINS=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

Generate the encryption key — it is what protects every token your users connect:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> Changing this key later makes already-stored tokens unreadable and they must be
> reconnected. Keep it.

### Step 5 — Run the backend

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health        # {"status":"ok"}
```

If a variable is missing, the API answers **503 naming it** — that is the design, not a
crash.

### Step 6 — Configure and run the frontend

```bash
cd ../frontend
npm install
cp .env.example .env
```

```env
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...          # anon key — public by design
# VITE_API_URL stays empty in dev: Vite proxies to 127.0.0.1:8000, so no CORS setup
```

```bash
npm run dev
```

Open <http://localhost:5173> and create an account. Sign-up and sign-in are handled by
Supabase Auth.

### Step 7 — Create a project

Give it a **name** and a **goal**. The goal is what every finding is judged against, so
write the real one: *"Ship the v2 payments launch to customers by Oct 31."*

### Step 8 — Connect the apps (on the project's Connections page)

Connect as few or as many as you like — the agent works with what it can reach.

| App | What to paste | Where to get it | Notes |
|---|---|---|---|
| **Slack** | bot token (`xoxb-…`) | <https://api.slack.com/apps> | scopes `channels:history`, `groups:history`, `channels:read`, `groups:read`, `users:read` — and **invite the bot to the channels** |
| **Linear** | personal API key | Settings → API → Personal API keys | |
| **GitHub** | fine-grained token + `owner/repo` | <https://github.com/settings/personal-access-tokens> | read access to that one repository |
| **Google** | click **Connect** → consent screen | see below | one consent covers Gmail, Drive and Calendar |

Each token is verified against the live API before it is stored, so a wrong paste fails
immediately with the app's own error rather than silently later.

**Google OAuth, one-time setup for the deployment:** create a **Web application** OAuth
client at <https://console.cloud.google.com/apis/credentials>, enable the Gmail, Drive
and Calendar APIs, request scopes `gmail.readonly`, `gmail.send`, `drive.readonly` and
`calendar.events`, and register this exact redirect URI:

```
http://localhost:8000/integrations/google/callback
```

Then add to `backend/.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_CALENDAR_ID=primary
```

The client id and secret identify the *application*; each project's own grant is stored
encrypted against that project.

### Step 9 — Run the first analysis

Click **Analyze**. The workflow fans out, collects, reasons, and writes back a health
state, findings and a proposed plan. The activity log shows what each app contributed.

### Step 10 — Approve a plan

Review the recovery plan, tick the actions you agree with, click **Approve & execute**.
Only those rows run; each records the integration's own result. Nothing else was ever
going to reach your workspace.

---

## 10 · Using the app

| Screen | What it is for |
|---|---|
| **Dashboard** | Every project with its current health, finding counts and last run |
| **Project** | The latest analysis: summary, findings with evidence, recovery plan, run history, activity log |
| **Ask** | A question about this project, answered only from collected evidence, with citations |
| **Connections** | Connect, verify and disconnect this project's apps |

Day to day: **Sync** before a status meeting, read the findings, approve the plan.

---

## 11 · Tests and checks

```bash
# backend — 114 tests, no network, no real database
cd backend && .venv/bin/python -m pytest tests -q

# frontend — type-checks and builds
cd frontend && npm run build
cd frontend && npm run lint
```

The backend suite uses the `client` fixture, which swaps Supabase for
`tests/fake_db.py`, and tests behaviour a user would notice rather than internals.

---

## 12 · Troubleshooting

| Symptom | Cause and fix |
|---|---|
| **503** with a variable name | That variable is missing from `backend/.env`. Add it and restart. |
| **401** on every call | Not signed in, or the session expired. Sign in again. |
| **404** on a project you believe exists | Wrong account — a project you do not own answers 404 on purpose. |
| **502 "did not return a valid …"** | The model answered with nothing usable. Retry; check `GEMINI_API_KEY` and quota. |
| **502 "Database error"** | `schema.sql` has not been run, or was run against a different project. |
| Analysis finds nothing | No app is connected, or the connected ones hold nothing about this project. Read the run's activity log — it names each app and what it returned. |
| Slack returns 0 items | The bot is not in the channel. Invite it. |
| Browser shows raw JSON on a project page | Stale dev server — restart `npm run dev`; the Vite proxy bypasses HTML requests. |
| Frontend throws "Missing VITE_SUPABASE_URL" | `frontend/.env` is missing. Copy `.env.example` and fill it in. |

---

## 13 · Current status and roadmap

**Working end to end:** authentication, projects, per-project encrypted integration
credentials, the full LangGraph workflow, persistence of every run with its evidence,
findings, actions and activity, the approval gate, the executor, Ask, and the React UI
over all of it. 114 backend tests pass.

All six integration modules are implemented against the real APIs with `httpx` — no
vendor SDKs — and each one is a single file that collects evidence and, where the app is
a write target, executes approved actions.

**Next**

- Move Google from one deployment-wide OAuth client to fully per-project consent
- Surface progress and per-run activity more prominently in the project view
- Widen write-back coverage (Slack replies, GitHub issue comments)
- Scheduled syncs instead of on-demand only
