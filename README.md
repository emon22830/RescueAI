# AI Project Rescue

**Projects don't fail silently — they fail in six different apps at once.**

The status in Linear says *In Progress*. The Slack thread says the API contract changed
three weeks ago. The spec in Drive still describes the old one. The client email asking
about the launch date is unanswered. Nobody is lying; nobody is looking at all six places
at the same time.

AI Project Rescue is an agent that does exactly that. It pulls evidence out of the tools a
team already uses, cross-references it against the project goal, names the blockers and
risks with the receipts attached, drafts a recovery plan, and — only after a human ticks
the box — executes that plan back into those same tools.

```
Collect evidence → Understand state → Detect blockers → Recovery plan
      ↑                                                      ↓
   Sync again  ←  Execute actions  ←  Human approval  ←──────┘
```

---

## What it actually produces

| | |
|---|---|
| **Evidence** | A normalized fact from one app — a Slack message, a Linear issue, a PR, a doc, a calendar event. |
| **Finding** | A blocker or risk, with a severity, a confidence score, and the exact evidence items that support it. |
| **Recovery plan** | 4–5 concrete actions (`update_issue`, `create_event`, `send_email`) — each tied to a finding, none executed without approval. |

A finding is only considered useful if it connects evidence from **more than one source**.
Anyone can read a single task list; the value is in the contradiction between them.

---

## External tools and services

**Services the agent reads from and writes back to**

| App | What it investigates | Write actions |
|---|---|---|
| Slack | What the team is actually saying | — |
| Gmail | Stakeholder communication | `send_email` |
| Google Drive | Requirements and specs | — |
| Linear | Task status and due dates | `update_issue` |
| GitHub | Commits, PRs and issues | — |
| Google Calendar | Meetings and deadlines | `create_event` |

**Platform**

| Layer | Choice |
|---|---|
| LLM | **Claude** (`claude-opus-5`) via the Anthropic Python SDK |
| Agent orchestration | **LangGraph** — parallel fan-out, one shared state |
| Backend | **FastAPI** + Pydantic (Python 3.14) |
| Database | **Supabase** (Postgres) |
| Frontend | **React 19** · Vite · TypeScript · Tailwind CSS 4 |

---

## How it works

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

Three design decisions worth a minute of a judge's attention:

**1. The investigators run in parallel.** `evidence` is an `Annotated[list, operator.add]`
in [state.py](backend/app/agents/state.py), so all three branches append to the same list
without overwriting each other. `risk` waits for all three before it runs.

**2. Findings cite evidence by index.** The `risk` agent is handed numbered evidence and
must return `evidence_indexes`. Those indexes are resolved back to the real items in
[risk.py](backend/app/agents/risk.py#L60), so every finding points at an actual Slack
message or Linear issue — the model cannot paraphrase a source into existence.

**3. Nothing is executed by an agent.** `recovery` only *proposes*. The plan is written to
the `actions` table as `pending`, and [executor.py](backend/app/agents/executor.py) — which
has no LLM in it at all — runs only the rows a human approved through the UI.

### API

| Method | Path | Purpose |
|---|---|---|
| POST | `/projects` | Create a project |
| GET | `/projects` | List projects |
| GET | `/projects/{id}` | One project plus its health summary |
| POST | `/projects/{id}/analyze` | Run the agent workflow |
| POST | `/projects/{id}/sync` | Run it again to pick up changes |
| GET | `/projects/{id}/findings` | Blockers and risks, with evidence |
| GET | `/projects/{id}/runs` | Analysis history |
| GET | `/projects/{id}/actions` | Proposed and executed actions |
| POST | `/projects/{id}/actions/approve` | Approve and execute |

### Layout

```
backend/app/
  api/            HTTP endpoints — three routers, nothing else
  projects/       project business logic, persistence of runs
  agents/         the LangGraph workflow and its six nodes
  integrations/   one file per external app: collect_evidence + execute_action
  ai/llm.py       the only place that talks to an LLM
  db/supabase.py  database client
frontend/src/
  pages/          Dashboard · Project · Connections
  features/       projects, intelligence (findings/actions), integrations
  lib/api.ts      typed client for every endpoint above
```

---

## Running it

**Prerequisites:** Python 3.12+, Node 20+, a Supabase project, an Anthropic API key.

### 1. Database

Open the Supabase SQL editor and run [backend/schema.sql](backend/schema.sql) once. It
creates `projects`, `integrations`, `agent_runs`, `evidence`, `findings` and `actions`.

### 2. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env       # then fill it in — see below
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Minimum needed to boot and analyze:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-opus-5
```

Add integration credentials (`SLACK_BOT_TOKEN`, `LINEAR_API_KEY`, `GITHUB_TOKEN`,
`GOOGLE_*`) as you wire each app up. Check it's alive:

```bash
curl http://localhost:8000/health     # {"status":"ok"}
```

Interactive API docs: <http://localhost:8000/docs>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/projects` and `/health` to port 8000, so no
CORS setup or `VITE_API_URL` is needed for local development.

### 4. Tests

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

---

## 2-minute hackathon demo

**Before you start:** backend running on :8000, frontend on :5173, a project already
created and analyzed once so there are findings on screen. Have a second browser tab open
on Linear (or whichever integration you wired) to show the write-back landing.

| Time | Screen | What you say |
|---|---|---|
| **0:00–0:20** | Dashboard | "A project goes off the rails in six apps at once. Linear says in progress, Slack says the API changed, the spec in Drive is stale, and the client email is unanswered. No single tool knows the project is in trouble." |
| **0:20–0:35** | Connections page | "We connect the six tools the team already uses. No new process, no new place to update status." |
| **0:35–1:00** | Project page → click **Sync project** | "One click. Three agents fan out in parallel — communication hits Slack and Gmail, engineering hits GitHub and Linear, requirements hits Drive and Calendar. Claude cross-references all of it against the project goal." |
| **1:00–1:25** | Findings, expand one card | "Here's the blocker. Severity high, confidence 0.9 — and every finding carries the actual evidence it came from: *this* Slack message, *this* Linear issue. The model cites evidence by index, so it can't invent a source." |
| **1:25–1:50** | Recovery plan → **Approve & execute** | "It doesn't just diagnose. It proposes the fix — reassign this issue, book this meeting, email the client. Nothing runs until a human approves. I approve…" *(switch tab)* "…and the issue is updated in Linear." |
| **1:50–2:00** | Back to dashboard | "Evidence in, blockers out, plan executed, human in the loop. That's AI Project Rescue." |

**The one line to land:** *every finding is backed by evidence the agent can point at, and
no action reaches a real tool without a human approving it.*

**If the demo gods are unkind:** run the analysis beforehand and demo `Sync project` on a
project that already has findings — the page re-renders the stored run, so a slow LLM call
or a rate-limited integration never dead-airs the pitch.

---

## Current status

The workflow runs end to end — supervisor → three parallel investigators → risk →
recovery → approval → executor — and the run, evidence, findings and actions are all
persisted per project.

The six integration modules in [backend/app/integrations/](backend/app/integrations/) are
scaffolded but return no evidence yet, so out of the box the agent correctly finds nothing.
Each is a single file with two functions. Implement them in this order:

1. `slack.py` — `collect_evidence`
2. `linear.py` — `collect_evidence` + `execute_action` (`update_issue`)
3. `github.py` — `collect_evidence`
4. `calendar.py` — `execute_action` (`create_event`)
5. `gmail.py` — `collect_evidence` + `execute_action` (`send_email`)
6. `drive.py` — `collect_evidence`

`collect_evidence` only has to return `list[Evidence]`. The agents, the prompts, the
persistence and the UI already handle everything downstream.
