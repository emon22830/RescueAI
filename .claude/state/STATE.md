# Where the project is

**Updated:** 2026-09-14 · **Version:** 0.1.0 · **Phase:** 1 of 4 — Foundation

## In one paragraph

The full loop is wired end to end and runs. A project can be created, the LangGraph
workflow executes all six nodes, and results are stored and rendered. What it cannot
do yet is find anything: every integration returns `[]`, so the agent correctly
reports no findings. The next work is filling in integrations, starting with Slack.

## Done

- Repo on GitHub, one clean commit, pushed to `main`
- Backend: FastAPI app, config, Supabase client, project service, 10 endpoints
- LangGraph workflow: supervisor → 3 parallel investigators → risk → recovery
- Evidence / Finding / PlannedAction models
- Supabase schema for all 6 tables (`backend/schema.sql`)
- Frontend: dashboard, project and connections pages, typed API client
- 12 backend tests passing

## Not done

- Every file in `backend/app/integrations/` returns `[]` — nothing is implemented
- `schema.sql` has never been run against a real Supabase project
- No `.env` exists, so no endpoint that touches the database has run live
- The demo project does not exist yet in any real app

## Next three tasks

1. Create the Supabase project, run `backend/schema.sql`, fill `backend/.env`,
   confirm `POST /projects` works against the live database.
2. Implement `integrations/slack.py → collect_evidence`.
3. Implement `integrations/linear.py → collect_evidence` and
   `execute_action("update_issue")`.

## How to run it

```bash
# backend  → http://localhost:8000
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
cd backend && .venv/bin/python -m pytest tests -q

# frontend → http://localhost:5173
cd frontend && npm run dev
```

If `.venv` is missing: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
