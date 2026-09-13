# Changelog

Semver. MAJOR = breaking contract or schema. MINOR = shipped feature. PATCH = fix.

## [0.2.0] — 2026-09-14

### Added
- **The agent workflow is connected to the application.** `POST /projects/{id}/analyze`
  runs the LangGraph workflow and persists, in one run: the agent run, the evidence, the
  findings with the evidence each one cites, the proposed actions, and the project state
  the agent concluded with — health, a written summary, and progress when the evidence
  measures it (see [[adr-0009]], [[adr-0010]])
- `POST /projects/{id}/sync` — the same investigation, re-run to pick up what changed in
  the connected apps; `triggered_by` tells the two apart in the run history
  (see [[adr-0011]])
- `GET /projects/{id}/findings`, `/runs` and `/actions`, all reading from the latest
  completed run so a sync replaces the dashboard instead of appending to it
- Every run stores its own `activity` log — which agent called which app and what came
  back — so an unconnected app is visible as "gmail: 0 items" rather than silence
- `agent_runs` columns: `triggered_by`, `health`, `summary`, `progress`, `activity`
- `tests/test_analysis_api.py` — the flow end to end through the real app, stubbing only
  the integrations and the LLM
- `tests/test_integrations.py` — every unconnected integration returns `[]` and is
  forbidden from touching the network, which is [[adr-0002]] made enforceable
- All six integrations implemented against the real APIs, `httpx` only, no SDKs:
  - **Slack** — channels the bot is in, messages from the last 30 days that name the
    project or sit in a channel named after it, author names resolved
  - **Gmail** — mail from the last 60 days matching the project, text body decoded
  - **Drive** — files whose content mentions the project, Docs/Sheets/Slides exported
    to text so the agent reads the spec rather than its filename
  - **Linear** — the matching project plus its issues, each with state, assignee and
    due date; `update_issue`, `assign_task`, `update_due_date`
  - **GitHub** — commits, pull requests and issues from the last 30 days of the repo
  - **Calendar** — events from the week just gone to 90 days out; `create_event`
- `integrations/google_auth.py` — one cached Google access token for the three Google
  APIs (see [[adr-0008]])
- `SLACK_CHANNEL_IDS` and `GOOGLE_CALENDAR_ID` settings; `.env.example` now names the
  scopes each credential needs

### Changed
- An integration with no credential logs a warning and contributes no evidence instead
  of failing the run; API errors still raise (see [[adr-0007]])
- The project summary carries `summary` and `progress` alongside `health` and the counts,
  and health is read back from the run that concluded it rather than recomputed from the
  stored severities (see [[adr-0010]])
- An unknown project id is now a 404 on `/findings`, `/runs` and `/actions` instead of an
  empty list (see [[adr-0012]])

### Known gaps
- No credentials exist yet, so no integration has been run against a live workspace
- Nothing has run against a live Supabase project; the five new `agent_runs` columns
  have never existed in a real table
- 43 tests pass, but every one of them stubs either the database, the integrations or
  the LLM. Nothing here is proof that the real services agree.

## [0.1.0] — 2026-09-14

### Added
- FastAPI application with CORS and centralized error handling
  (503 missing config · 404 unknown project · 502 database · 422 validation)
- Configuration via `backend/.env`, with an error naming every missing variable
- Supabase client and schema for `projects`, `integrations`, `evidence`, `findings`,
  `agent_runs`, `actions`
- Project service: create, list, get, health summary, analyze, approve
- 10 endpoints, all with typed Pydantic request and response models
- One LangGraph workflow: supervisor → communication · engineering · requirements
  (parallel) → risk → recovery, plus a non-LLM executor
- `Evidence`, `Finding`, `PlannedAction` models
- React 19 + Vite + TypeScript + Tailwind frontend: dashboard, project and
  connections pages, typed API client, evidence shown behind a "Why?" toggle
- 12 backend tests running the real app against an in-memory database

### Known gaps
- All six integrations return `[]` — see [[BLOCKERS]] *(resolved in 0.2.0)*
- Nothing has run against a live Supabase project
