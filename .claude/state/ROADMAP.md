# Roadmap

Phases map to versions. Priority order is fixed: if time runs out, phases 1–3 are what
must work.

## Phase 1 — Foundation → v0.1.0 ✅
Repo, backend, workflow skeleton, schema, frontend shell, tests.

## Phase 2 — The loop works for real → v0.2.0 ✅
The analysis flow wired end to end and persisted: supervisor → investigators → risk →
recovery, every run storing its evidence, findings, proposed actions and the project
state the agent concluded with. Auth, per-project encrypted credentials, and the
approval gate in the UI.

## Phase 3 — The loop runs itself, and can actually act → v0.4.0 ◀ current

1. ✅ Every integration can be written to, not just read — 31 action types across nine
   apps, covering create, update, delegate, close and message
2. ✅ One catalog (`executor.ACTION_TYPES`) that the recovery prompt is generated from
   and the dashboard is served, so the three can never disagree
3. ✅ Analysis is accepted, not awaited — `/analyze` returns a queued run and the work
   happens behind the request
4. ✅ Continuous monitoring — a per-project schedule and an in-process loop that runs
   what is due
5. ✅ In-app notifications when a scheduled run changes a project's verdict, or fails
6. ✅ Actions taken directly from the dashboard, without waiting for a plan
7. ✅ Ten connectors — the four trackers a real team might use (Linear, Jira, Asana,
   Trello) rather than assuming one
8. ⬜ **Migrations 0002–0004 run against the live database.** Everything above is code
   until this happens.
9. ⬜ **One real analysis, on real evidence, from a live workspace.** `findings` has
   never had a row in it.
10. ⬜ **One approved action executed against a real workspace.**

**Done when:** a blocker that exists only in the combination of two apps is surfaced,
explained with links to the real messages, and fixed by an action a human approved.

## Phase 4 — Demo and hardening → v1.0.0
- The "SaaS Product Launch" scenario seeded in real connected workspaces
- The end-to-end run rehearsed against live credentials
- Google moved from one deployment-wide OAuth client to per-project consent
- A shared work queue, so more than one backend instance can run schedules safely

## Explicitly out of scope
Real-time sync, RAG or embeddings, a second LangGraph workflow, an SDK per vendor.

## Superseded
- ~~"Background workers are out of scope; manual Sync Now is sufficient."~~ Reversed in
  v0.3.0 — a tool that only looks when somebody clicks is not monitoring anything. The
  scheduler is one in-process asyncio loop, which is the smallest thing that could
  work ([[adr-0016]]).
