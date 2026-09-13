# Roadmap

Phases map to versions. Priority order is fixed: if time runs out, phases 1–2 are
what must work.

## Phase 1 — Foundation → v0.1.0 ✅
Repo, backend, workflow skeleton, schema, frontend shell, tests.

## Phase 2 — The loop works for real → v0.2.0 ◀ current
The nine things that must survive any time cut.

1. Live Supabase — schema applied, `.env` filled, endpoints verified against it
2. ✅ Slack `collect_evidence`
3. ✅ Linear `collect_evidence` + `execute_action("update_issue")`
4. ✅ GitHub `collect_evidence`
5. Risk agent producing real findings from real evidence — wired and persisted, still
   waiting on real evidence and an `ANTHROPIC_API_KEY` to judge the prompt
6. Recovery agent producing a real plan — same: wired and persisted, never run for real
7. Approval gate in the UI
8. Real execution writing back to Linear
9. Dashboard showing it

**Done when:** a blocker that exists only in the combination of Slack + Linear + GitHub
is surfaced, explained with links, and fixed by an approved action.

## Phase 3 — The remaining three apps → v0.3.0
10. ✅ Gmail `collect_evidence` + `execute_action("send_email")`
11. ✅ Drive `collect_evidence`
12. ✅ Calendar `collect_evidence` + `execute_action("create_event")`

Code is written for all three; none has been run against a live account yet.

## Phase 4 — Demo polish → v1.0.0
The "SaaS Product Launch" scenario seeded across all six real workspaces, the
end-to-end run rehearsed, loading and error states tidy.

## Explicitly out of scope
Real-time sync, OAuth for multiple users, RAG or embeddings, multi-tenant auth,
background workers. Manual "Sync Now" is sufficient.
