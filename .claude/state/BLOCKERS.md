# Open blockers

Resolved items move to CHANGELOG.md. Never delete one silently.

## 1 — Migrations 0002, 0003 and 0004 have not been run against the live database

Continuous monitoring and notifications are written, tested and shipped in code, but the
live Supabase project is still on the pre-scheduling schema. Verified this session:
`projects` has no `sync_interval_minutes` or `last_synced_at`, and `notifications` does
not exist (`PGRST205`).

**Symptoms until it is run:** `PUT /projects/{id}/schedule` answers **502**, the bell
stays empty, and the scheduler ticks but finds nothing due — `_is_due` reads a column
that is not there, gets `None`, and correctly decides nothing is scheduled.

`0003_actions_from_the_dashboard.sql` is outstanding too: `actions.run_id` is still
`not null` and there is no `origin` column, so `POST /projects/{id}/actions` — taking an
action from the dashboard — answers **502** until it is run.

`0004_more_connectors.sql` is outstanding too. Three check constraints name every app by
hand — `evidence.source`, `actions.integration` and `integrations.provider` — so until it
runs, connecting Jira, Notion, Asana or Trello fails, and any evidence collected from
them violates a constraint mid-run.

**Unblocks when:** `0002`, `0003` and `0004` in `backend/migrations/` have all been run
in the Supabase SQL editor, in that order. All three are safe on an existing database —
every statement is `if not exists`, a constraint swap, or a `drop not null`.

**Why analysis still works meanwhile:** `_touch_synced` and `_notify` both swallow and
log their own failures on purpose, so a database missing those columns cannot strand a
run as `running` forever. That is deliberate, and it is the reason the system stayed
runnable through this change — not an accident to be tidied away.

## 2 — No demo data in the real apps

The agent is only as good as what it can find. The "SaaS Product Launch" scenario —
the Slack thread about the blocked payment API, the requirements-change email, spec v3
in Drive, overdue PAY-124 in Linear, the launch review in Calendar — has to exist in
real connected workspaces before any demo is possible.

Live state as of this session: 4 projects, 4 runs, **0 findings**. Only GitHub and
Google are connected on any project; Slack and Linear — the two richest sources — are
not connected anywhere, which is most of why nothing has been found yet.

**Never solve this by hardcoding data in source.** See [[adr-0002]].

## 3 — No write action has touched a live workspace

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

## Traps worth knowing

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
