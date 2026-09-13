# Changelog

Semver. MAJOR = breaking contract or schema. MINOR = shipped feature. PATCH = fix.

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
- All six integrations return `[]` — see [[BLOCKERS]]
- Nothing has run against a live Supabase project
