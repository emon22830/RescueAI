# Where the project is

**Updated:** 2026-09-14 · **Version:** 0.2.0 · **Phase:** 2 of 4 — The loop works for real

## In one paragraph

The analysis flow is now wired end to end and proven: `POST /analyze` runs the LangGraph
workflow, and the run, its evidence, its findings, its proposed actions and the project
state the agent concluded with (health, summary, progress) are all persisted and read
back by `/findings`, `/runs` and `/actions`. Forty-three tests drive that whole path
through the real FastAPI app against an in-memory stand-in for Supabase. What is still
unproven is everything that needs a credential: `backend/.env` does not exist, so no
integration has touched a live workspace and no query has touched a live database. The
next work is credentials, one app at a time, starting with Supabase itself.

## Done

- Repo on GitHub, pushed to `main`
- Backend: FastAPI app, config, Supabase client, project service, 10 endpoints
- LangGraph workflow: supervisor → 3 parallel investigators → risk → recovery
- **The analysis flow is connected to the application.** `analyze` and `sync` run the
  workflow and persist the agent run, evidence, findings, proposed actions, and the
  project state — health, summary, and progress when the evidence measures it
- Every run stores its own activity log, so a user can see that Gmail contributed
  nothing because it is not connected
- `/findings`, `/runs` and `/actions` read from the latest completed run; a sync
  replaces what the dashboard shows instead of piling onto it
- **All six integrations implemented** — every one normalizes to `Evidence` in its own
  file, and the three write targets (Linear, Calendar, Gmail) execute real actions
- `integrations/google_auth.py`: one cached token for Gmail + Drive + Calendar
- 43 backend tests passing, including a guard that every unconnected integration
  returns `[]` and never reaches the network

## Not done

- No `backend/.env` exists — every integration logs "skipped" and returns `[]`, and
  every endpoint that touches the database returns 503
- `schema.sql` has never been run against a real Supabase project. It has grown five
  columns on `agent_runs` (`triggered_by`, `health`, `summary`, `progress`, `activity`)
  that have therefore never existed in a real table
- **No integration has been called against a live workspace.** The request shapes come
  from the current API docs and the normalizers are verified against doc-shaped
  payloads, but nothing has round-tripped a real token yet
- The demo project does not exist yet in any real app
- The frontend types mirror the new response shapes, but no page renders `summary`,
  `progress` or a run's `activity` yet

## Next three tasks

1. Create the Supabase project, run `backend/schema.sql`, fill `SUPABASE_URL` and
   `SUPABASE_SERVICE_KEY` in `backend/.env`, confirm `POST /projects` works against the
   live database and that PostgREST accepts `activity` as jsonb.
2. Add `SLACK_BOT_TOKEN`, invite the bot to the project channel, and verify:
   `.venv/bin/python -c "from app.integrations import slack; print(slack.collect_evidence('SaaS Product Launch'))"`
3. Add `ANTHROPIC_API_KEY` and `LINEAR_API_KEY`, then run one real
   `POST /projects/{id}/analyze` and read the summary it writes — this is the first time
   the risk prompt will be judged on real evidence rather than a stub.

## Credentials each integration needs

| App | Variables | Notes |
|---|---|---|
| Slack | `SLACK_BOT_TOKEN`, optional `SLACK_CHANNEL_IDS` | scopes: `channels:history`, `groups:history`, `channels:read`, `groups:read`, `users:read`; the bot must be invited to the channels |
| Linear | `LINEAR_API_KEY` | personal API key, sent raw in `Authorization` — no `Bearer` |
| GitHub | `GITHUB_TOKEN`, `GITHUB_REPO` | `GITHUB_REPO` is `owner/name` |
| Gmail · Drive · Calendar | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CALENDAR_ID` | one OAuth client; scopes `gmail.readonly`, `gmail.send`, `drive.readonly`, `calendar.events` |

## How to run it

```bash
# backend  → http://localhost:8000
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 --host ::
cd backend && .venv/bin/python -m pytest tests -q

# frontend → http://localhost:5173
cd frontend && npm run dev
```

If `.venv` is missing: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
