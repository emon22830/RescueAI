# Where the project is

**Updated:** 2026-09-14 · **Version:** 0.6.1 · **Phase:** 4 of 4 — Live, and hardened for it

## In one paragraph

RescueAI does the whole job it was designed for, and it is deployed. It reads ten apps,
reasons over the evidence, names blockers with the evidence attached, proposes a recovery
plan, and — once a human approves — carries it out in nine of the ten across 31 action
types. It re-analyses on a schedule and tells the owner in the app when the verdict
changes. Backend on Render, frontend on Vercel, both deploying from `main` on push, with
CI running the suite on every push and pull request. 244 backend tests and 8 frontend
tests back it, and the backend suite is hermetic.

**This session was production hardening, and it found real bugs.** The one that mattered
most had been mis-diagnosed twice: opening a project returned 500s because all seven of
the page's parallel requests shared one Supabase client across seven worker threads, and
HTTP/2 multiplexing over a single connection is not safe to drive that way
([[adr-0023]]). It was hard to see because an unhandled error was being answered
*outside* the CORS middleware, so it reached the browser as "backend unreachable" rather
than as a 500 ([[adr-0024]]). Both are fixed. Separately, a production build with no
`VITE_SUPABASE_URL` was silently tree-shaking the entire app away and deploying a white
screen with a green build ([[adr-0025]]).

What is still unproven is unchanged and narrow: **no write action has been executed
against a real workspace**, and no finding has ever been produced from live evidence
because only one app is connected on any project.

## Done

- Backend: FastAPI, config, Supabase client, project service, **23 endpoints**
- Auth: Supabase Auth, per-project ownership checked in `service.py`, never from the URL.
  A verified token is remembered for 60s so one screen does not cost seven Auth hops
  ([[adr-0028]])
- Per-project encrypted credentials for Slack/Linear/GitHub, per-project Google consent
- LangGraph workflow: supervisor → 4 parallel investigators → risk → recovery
- **Ten integrations collect; nine execute, across 31 action types** ([[adr-0021]])
- **One catalog, `executor.ACTION_TYPES`, is the contract** between planner, API and UI
  ([[adr-0018]])
- **Continuous monitoring** ([[adr-0016]]) and **in-app notifications** ([[adr-0017]])
- **Migrations 0002–0005 are applied to the live database** and a full analysis has
  completed end to end: 10 real GitHub commits with working URLs, project state written
  by the risk agent, Ask answering from that evidence with citations

### Deployed and verifiable

- **Backend** https://rescueai-xkhy.onrender.com · **Frontend** https://rescue-ai-self.vercel.app
- `GET /health` reports `{"status","version","commit"}`. `commit` comes from
  `RENDER_GIT_COMMIT` and is **the way to tell a deploy that landed from one still
  rolling out** — without it, a pushed fix and a live one are indistinguishable, which
  cost real time this session
- Render builds from the `backend/` root, so a commit touching only `.github/` or docs
  correctly does **not** redeploy it. A stale `commit` there is not always a problem
- CI (`.github/workflows/ci.yml`): backend tests, frontend lint/test/build, and a check
  that the emitted bundle still contains the app
- `main` is protected — required checks, no force-push, no deletion, admins exempt
  ([[adr-0027]])
- Dependencies pinned, Dependabot opens weekly grouped updates ([[adr-0026]])

### Fixed this session

- **The 500s behind "Project unavailable"** — one Supabase client shared across worker
  threads ([[adr-0023]]). This is the real cause; CORS and a key mismatch were both
  wrong guesses
- **Errors that looked like outages** — a 500 answered outside CORS reaches the browser
  as unreachable ([[adr-0024]])
- **Builds that ship an empty app** — 262 kB instead of 581 kB, exit 0 ([[adr-0025]])
- **A dead session with no way out** — the frontend now refreshes an expired token once,
  retries, and signs out if it is really gone. The refresh is shared across concurrent
  requests because Supabase rotates the refresh token, so refreshing per failure ends a
  session that only needed renewing. Eight tests cover it
- **CORS rejecting every origin** — `settings.allowed_origins` tolerates a trailing
  slash, wrapping quotes and stray spacing, because a malformed value fails invisibly
- **Ask burning 90 seconds on a refused quota** — `ProviderError` is handled, and the
  retry honours the provider's own `RetryInfo` instead of guessing
- **One failed request blanking a loaded page** — `ProjectPage` uses `allSettled`

## Not done

- **No write action has been executed against a live workspace.** Shapes match current
  API docs and are pinned by tests down to the JSON body, but nothing has round-tripped
  a real token
- **No finding has ever come from live evidence** — `findings` has 0 rows. Only GitHub
  and Google are connected anywhere; Slack and Linear, the two richest sources, are not
  connected on any project
- The demo scenario does not exist in the real workspaces (blocker 2)
- **The deploy is not gated by CI.** Render and Vercel deploy in parallel with the
  checks, so a red build still ships ([[adr-0027]])
- No error tracking — a failure reaches Render's logs and nowhere else
- `/health` does not check its dependencies: it reports `ok` when Supabase is unreachable

## Next three tasks

1. **Connect Slack on one live project and execute one write.** This closes the last
   unproven path *and* the richest evidence gap in one move. `post_message` is the
   sharpest test: it is the only write with a lookup in front of it (`resolve_channel`
   turns `#payments` into a channel id) and it needs `chat:write`, which is **not** in
   the scope list collection asks for — an existing bot token will be rejected until the
   scope is added and the app reinstalled. Take the action from the dashboard composer.
2. **Get a second app onto that same project and re-run the analysis**, so the risk agent
   is judged on *cross-app* evidence. Today's live run had GitHub alone, and a finding is
   only worth reading when it connects two sources — with one app, 0 findings is correct
   but proves half the prompt.
3. **Gate the deploy, or decide not to.** Two changes per service and both halves matter:
   add a deploy hook as `RENDER_DEPLOY_HOOK_URL` / `VERCEL_DEPLOY_HOOK_URL`, *and* turn
   auto-deploy off on that service. Adding only the hook deploys everything twice. The
   `deploy` job already reads both and skips whichever is absent.

## How to run it

```bash
# backend  → http://localhost:8000   (the scheduler starts with it)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 --host ::
cd backend && .venv/bin/python -m pytest tests -q        # 244 tests, hermetic

# frontend → http://localhost:5173
cd frontend && npm run dev
cd frontend && npm test && npm run lint && npm run build  # 8 tests
```

`npm run build` **fails** without `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in
`frontend/.env`. That is deliberate ([[adr-0025]]) — without it the build silently emits
an app with no app in it.

The scheduler is in-process: monitoring only runs while the backend runs. Set
`SCHEDULER_ENABLED=false` on any second instance, or both pick up the same project.

If `.venv` is missing: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

```bash
# Is my fix live?
curl https://rescueai-xkhy.onrender.com/health
```
