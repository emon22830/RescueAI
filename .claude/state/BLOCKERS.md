# Open blockers

Resolved items move to CHANGELOG.md. Never delete one silently.

## 1 — No demo data in the real apps

The agent is only as good as what it can find. The "SaaS Product Launch" scenario —
the Slack thread about the blocked payment API, the requirements-change email, spec v3
in Drive, overdue PAY-124 in Linear, the launch review in Calendar — has to exist in
real connected workspaces before any demo is possible.

Live state as of this session: 4 projects, 4 runs, **0 findings**. Only GitHub and
Google are connected on any project; Slack and Linear — the two richest sources — are
not connected anywhere, which is most of why nothing has been found yet.

**Never solve this by hardcoding data in source.** See [[adr-0002]].

## 2 — No write action has touched a live workspace

Nine integrations can now execute, across 31 action types. Every one is pinned by a test
down to the JSON body that goes over the wire, and the shapes come from the current API
docs — but none has round-tripped a real token.

The two riskiest both have to resolve something they were not given:

- **Slack `post_message`** turns `#payments` into a channel id via `users.conversations`.
  It also needs the `chat:write` scope, which is *not* in the scope list collection asks
  for — an existing bot token will be rejected until the scope is added and reinstalled.
- **Linear `create_issue`** has to pick a team (`resolve_team`): the one named in
  `params.team`, else the team behind the Linear project of the same name, else the only
  team there is. In a multi-team workspace with no match it refuses and lists the team
  keys rather than guessing — worth seeing that error once before a demo.

## 3 — The deploy is not gated by CI

CI runs on every push, but Render and Vercel redeploy on their own the moment `main`
moves — *in parallel* with the checks, not after them. A commit whose tests fail still
reaches production; the red check appears next to it a minute later.

**Unblocks when:** for each service, a deploy hook is saved as a repository secret
(`RENDER_DEPLOY_HOOK_URL`, `VERCEL_DEPLOY_HOOK_URL`) **and** auto-deploy is turned off on
that service. Both halves, together — adding only the hook deploys everything twice. The
`deploy` job in `ci.yml` already reads both and skips whichever is absent.

Related: `enforce_admins` is false on the branch protection, so the required checks gate
pull requests but not a maintainer's own push ([[adr-0027]]). Turn it on when a second
person has write access.

## 4 — A failure in production is only visible in Render's logs

There is no error tracking. When something throws, the catch-all middleware logs a
traceback where nobody is watching and the user sees a generic message. Every diagnosis
this session needed either a reproduction or a log read; neither scales past one
developer.

Half of this is now fixed: `GET /health/ready` reaches the database and answers 502/503
when it cannot, while `/health` keeps answering `ok` whenever the process is alive. They
are separate on purpose — a platform health check that goes red during a database blip
would restart a service whose code is fine. Nothing automated is wired to `/health/ready`
yet; it is there to be asked.

What is still missing is somewhere for a failure to *go*. An exception logs a traceback
in Render and notifies nobody.

## Traps worth knowing

- **`get_db()` must never be `@lru_cache`d again** ([[adr-0023]]). One shared client is
  one `httpx` client and one HTTP/2 connection driven from every worker thread; the
  loser gets `httpx.ReadError` and a healthy page renders as a crash. It reads as
  harmless memoisation. It is the bug.
- **Middleware order in `main.py` is load-bearing** ([[adr-0024]]). The last middleware
  added is the outermost, so the catch-all must be registered *before* `CORSMiddleware`.
  An `@app.exception_handler(Exception)` does not work here — it installs on
  `ServerErrorMiddleware`, outside CORS, and the 500 goes back with no headers.
- **A frontend build with no `VITE_SUPABASE_URL` exits 0 and ships nothing**
  ([[adr-0025]]). 262 kB instead of 581 kB. `vite.config.ts` now refuses it.
- **`secrets` is not readable from a workflow `if`** — at job or step level. It does not
  evaluate false, it fails the file to parse. Map to `env` on the job and test `env.X`.
- **Render builds from the `backend/` root**, so a commit touching only `.github/` or
  docs does not redeploy it. `/health`'s `commit` field is how you tell.
- **Pushing `.github/workflows/*` needs the `workflow` OAuth scope** on the `gh` login.
  Without it the push is rejected with everything else in the commit.
- `.env` is gitignored and the repo is **public**. Check before every push.
- SSH to GitHub fails (`Permission denied (publickey)`) — the key at
  `~/.ssh/id_ed25519.pub` is not registered on the account. The remote uses HTTPS
  through the `gh` CLI instead. See [[adr-0006]].
- `postgrest.APIError` is what the Supabase client raises; it is handled globally in
  `main.py`. Do not catch it per route.
- The run column is `triggered_by`, not `trigger` — `trigger` is a SQL keyword and not
  worth the quoting it would cost in every query.
- `analyze` and `sync` are one code path ([[adr-0011]]). Changing one changes both.
- **Never add an action type in only one place** ([[adr-0018]]). `executor.ACTION_TYPES`
  is the catalog; the prompt is generated from it and the UI is served it. Add the entry
  *and* the branch in the integration, or `test_every_catalogued_action_type_is_
  actually_dispatchable` fails — which is the point.
- **A connector is nine files, not one** ([[adr-0021]]). The `Source` literal, an
  investigator node, the executor catalog, the service token list, the API catalog,
  three SQL constraints and four frontend maps. The skill lists them all.
- **Never write an API client from memory.** Jira's search endpoint was removed outright
  in 2025; code written against the remembered one collects nothing and reports nothing.
- **Nothing secret goes in `extra`** on a connect request — it is stored as metadata and
  read back to the owner. Trello's `key` is there only because it identifies the app,
  not the user.
- **The test suite is hermetic and must stay that way** ([[adr-0022]]). The `db` fixture
  is autouse; do not add a test path that reaches `service.get_db()` unpatched.
- **`/analyze` returns 202 and a `queued` run, not a result** ([[adr-0015]]). Anything
  reading a run must handle one with no counts and no `completed_at` yet.
- **The scheduler only runs while the backend runs**, and only on one instance
  ([[adr-0016]]). Monitoring is not a hosted cron.
- `create table if not exists` does not add columns to a table that already exists.
  Every schema change needs a file in `backend/migrations/`, not just an edit to
  `schema.sql`. This has now bitten the project twice.
