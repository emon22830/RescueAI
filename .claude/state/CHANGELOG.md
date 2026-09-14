# Changelog

Semver. MAJOR = breaking contract or schema. MINOR = shipped feature. PATCH = fix.

## [0.6.0] — 2026-09-14

**The first analysis to run against a live workspace.** 10 real GitHub commits
collected with working URLs, project state written by the risk agent, Ask answering
from that evidence with citations. Two bugs surfaced that no test could have caught.

### Fixed
- **The recovery planner sent a schema Gemini refuses.** `_PlanStep.params` was
  `dict[str, str]`; a dict of arbitrary keys becomes an open-ended map, and the Gemini
  Developer API rejects the whole request. Every analysis that got as far as proposing
  a plan died at the last node, losing findings the risk agent had already produced.
  Now a list of `{name, value}` pairs — same capability, a schema the provider accepts.
- **A transient provider 503 threw away a whole investigation.** `gemini-3.8-flash`
  spent minutes answering "experiencing high demand"; the evidence had already been
  collected by then, and a scheduled run has nobody watching to retry. `llm.ask` and
  `ask_for` now share one `_generate` that retries 5xx and 429 four times (2s/6s/15s)
  and re-raises the real error when it gives up. A 4xx fails immediately — retrying our
  own mistake only hides it behind a delay.

### Added
- `tests/test_llm_schemas.py` — every model passed to `llm.ask_for` is checked
  structurally for open-ended maps and untyped fields, including a test that the guard
  still detects a known-bad model so it cannot pass vacuously
- `tests/test_llm_retry.py` — what is retried and what is not, without calling out
- `migrations/0005_finish_multi_tenant.sql` — finishes `0001`, which was left
  deliberately half-applied: the one ownerless project gets an owner and
  `projects.owner_id` becomes `not null`, matching what `schema.sql` always claimed
- `settings.allowed_origins` — forgiving CORS parsing (trailing slash, quotes, spacing)
  and a startup log line naming the origins, because a wrong value fails invisibly as
  "the backend is down" in every screen

### Operational
- Migrations 0002–0005 applied to the live Supabase project and verified by inserting
  exactly what the new code writes inside a rolled-back transaction
- 223 tests, still hermetic

## [0.5.0] — 2026-09-14

### Added
- **Four more connectors, so the product fits the stack a team already has.** Jira,
  Asana and Trello join Linear as trackers; Notion joins Drive for specs. All are token
  apps on the existing per-project model — no new environment variable, nothing shared
  ([[adr-0021]])
- **A fourth investigator, `delivery`**, reading every tracker. `engineering` keeps
  GitHub alone, because what a team built and what its plan says are different
  questions and the gap between them is the finding ([[adr-0020]])
- 31 action types across nine apps, up from 15 across five — create, update, delegate,
  close and message, in whichever tracker the team uses
- `migrations/0004_more_connectors.sql` — widens the three check constraints that name
  every app by hand (`evidence.source`, `actions.integration`, `integrations.provider`)
- 37 new tests, including the three shapes that are invisible until a live token is in
  play: Jira's replacement search endpoint, Jira's Atlassian Document Format, and
  Trello's credential riding in the query string. 203 total.

### Changed
- **The connect form is declarative.** `EXTRA_FIELDS` says what each app needs besides
  its credential, rather than a chain of `if (provider === …)` that ten apps would have
  made unreadable
- The tests that enumerated the six apps and three agents now derive them from
  `executor.INTEGRATIONS` and `supervisor.AGENTS`, so the next connector does not mean
  editing counts by hand
- Marketing and app surfaces read their app list from `SOURCE_ORDER` rather than
  repeating it — a landing page claiming an app the product lacks is the worst drift
- `.claude/skills/new-integration/SKILL.md` rewritten: it documented the old
  single-argument `collect_evidence(project_name)` and `settings`-based credentials,
  and would have produced a broken integration. It now carries the eight-place wiring
  checklist and names the tests that catch a missed step
- `.claude/state/ROADMAP.md` rewritten — it still listed background workers as out of
  scope and manual sync as sufficient, both reversed in 0.3.0

### Fixed
- **Frontend/backend contract drift, found by diffing the live OpenAPI schema against
  every `features/*/types.ts` interface.** All twelve response shapes now mirror exactly:
  `Evidence.metadata` was sent by the API and declared nowhere, and the API contract doc
  was missing it as well as the ask response's `kind` and `follow_ups`
- Stale claims on the landing page: "Three investigator agents" (four), "Three of them
  can also carry out an approved step" (nine), "Nothing reaches Linear, Gmail or
  Calendar until you tick it", and an FAQ naming only three token apps
- The Connections page's loading skeleton showed six cards for ten apps; it is now one
  per app, so the loading state is the shape of the result
- A project card's connector strip showed all ten apps with the unconnected ones faded
  and a "2/10 connected" count — which read as eight things wrong with a project that
  was fine, and stopped fitting a card on a phone. It now shows what the project is
  actually reading; what is left to connect is the Connections page's job
- `backend/.env.example` documented three token apps and none of the four new ones, and
  never mentioned that Slack's `chat:write` is needed for actions but not for reading —
  so an older bot token reads fine and fails on the first approved action
- The backend's integration catalog and the frontend's `SOURCE_ORDER` listed the apps in
  different orders, so the Connections page and every app strip disagreed
- **The test suite no longer touches the real Supabase project.** The `db` fixture is
  autouse, so a test cannot reach live data by forgetting to ask for it. Suite runtime
  fell from 2.7s to 0.4s, which is what exposed it ([[adr-0022]])

## [0.4.0] — 2026-09-14

### Added
- **One catalog of what the system can do.** `executor.ACTION_TYPES` — 15 types across
  five apps, each carrying the verb a manager would use (add · update · delegate ·
  close · message) and what its two fields mean. The recovery prompt is *generated*
  from it and the dashboard composer is *served* it, so a type cannot exist in one
  place and not the others ([[adr-0018]])
- **The missing verbs.** Linear `create_issue`, `comment_issue`, `close_issue` (with
  `resolve_team` so a new issue lands in the right team, and the team's own completed
  state rather than a guess at "Done"); GitHub `assign_issue` and `close_issue`;
  Calendar `update_event` and `cancel_event`. Every verb a recovery plan needs now
  exists in the app the work lives in.
- **Actions from the dashboard.** `POST /projects/{id}/actions` — a person takes one
  action directly, without waiting for the agent to propose it. Authored and approved
  in the same gesture, but the same row, the same states and the same guard in
  `executor.execute` ([[adr-0019]])
- `GET /projects/{id}/actions/types` — what this project can be asked to do, filtered
  to the apps it has connected, so the composer never offers an app it cannot reach
- `actions.origin` (`agent` | `user`) and a nullable `actions.run_id`, in
  `backend/migrations/0003_actions_from_the_dashboard.sql`
- The recovery planner can set a step's optional `params` (team, assignee, due_date,
  subject, start, minutes) — previously only `value` was reachable
- Frontend: a "Take an action" composer on the project page, grouped by verb and
  labelled in each action's own words; `Alert` gained a `success` tone
- 20 new tests, including a guard that every catalogued type is actually dispatchable
  and that the recovery prompt offers exactly what can be run. 166 total.

### Changed
- `get_actions` returns the latest run's plan **plus** anything the user did themselves,
  so a dashboard action survives a re-sync instead of vanishing with the run it happened
  to be contemporary with
- `ActionCard` says who wrote each action — "You" or "Agent"

## [0.3.0] — 2026-09-14

### Added
- **Slack and GitHub can be written to.** `slack.execute_action` posts a message
  (`post_message`, with `resolve_channel` turning `#payments` into a channel id);
  `github.execute_action` opens an issue (`create_issue`) and comments on one
  (`comment_issue`). Five of the six integrations now execute; Drive stays read-only.
- The recovery prompt offers the three new action types, so the planner can propose
  the step a delivery lead would actually take — telling the channel.
- **Continuous monitoring.** `PUT /projects/{id}/schedule` sets a per-project interval
  (hourly, 6-hourly, daily; floor 15 minutes). `app/scheduler.py` is one in-process
  asyncio loop, started and stopped by the FastAPI lifespan, that runs what is due
  ([[adr-0016]])
- **Notifications.** A scheduled run that changes a project's health, or fails, writes a
  row the owner sees in the app shell. In-app only, never posted to a workspace
  ([[adr-0017]]). `GET /notifications`, `POST /notifications/read`
- `notifications` table; `projects.sync_interval_minutes` and `projects.last_synced_at`;
  `agent_runs.status` gained `queued` and `triggered_by` gained `schedule` —
  all in `backend/migrations/0002_scheduling_and_notifications.sql`
- Frontend: a Monitoring card on the project page, a notification bell in the app shell,
  and a project page that follows a run to completion instead of blocking on the request
- `SCHEDULER_ENABLED` and `SCHEDULER_TICK_SECONDS` settings
- 31 new tests — `tests/test_write_actions.py` (the wire format of every new write) and
  `tests/test_scheduling.py` (the schedule, what is due, the tick, and notifications).
  146 total.

### Changed
- **`POST /analyze` and `/sync` now answer 202 with a `queued` run** and do the work
  behind the request ([[adr-0015]]). A failure is recorded on the run — `status`,
  `error`, `completed_at` — instead of raised as a 500 at a caller who may not exist.
- `writes_back` is now true for Slack and GitHub in the integrations catalog, so the
  Connections page stops calling them read-only
- `RunHistory` and `LatestAnalysis` render a run that has not finished as Queued or
  Investigating, with no counts — previously anything not failed read as "Completed"
- `due_projects` skips a project that already has a run in flight, so an analysis slower
  than its own interval cannot stack runs on itself
- `_touch_synced` and `_notify` log their own failures rather than propagating them: an
  analysis that finished is worth more than the bookkeeping about it

### Fixed
- A pre-scheduling database can no longer strand a run as `running` forever. Verified
  against the live Supabase project, which is still un-migrated — see blocker 1.

### Resolved
- **Blocker: no Supabase credentials.** `backend/.env` exists and the live project
  answers: 4 projects, 4 runs, 3 connected integrations. `schema.sql` applied cleanly
  and PostgREST returns every column the service expects, `activity` as jsonb included.

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
