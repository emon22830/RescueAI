# Decisions

Append-only. Never edit or delete an entry — mark it superseded and add a new one.
This file is the *why*; the code is the *what*.

---

## ADR-0001 — One LangGraph workflow, simple modular monolith
**2026-09-14 · active**

**Context.** Hackathon, short timeline, judges read the code.

**Decision.** A single LangGraph graph in `app/agents/graph.py`. No second graph, no
separate AI service, no repository pattern, no managers or factories, no
domain/application/infrastructure layers.

**Consequence.** Any file can be read top-to-bottom and understood. Architecture is not
the deliverable; a working loop is.

---

## ADR-0002 — Integrations never return fake data
**2026-09-14 · active**

**Context.** Mocking external apps is the fastest way to a demo and the fastest way to
build something that does not work.

**Decision.** An unimplemented integration returns `[]`. Synthetic demo data lives in the
real connected workspaces, never in our source.

**Consequence.** Today the agent honestly finds nothing. That is preferable to a demo
that collapses when a judge asks to see the live Slack thread. Blocks on [[BLOCKERS]] #2.

---

## ADR-0003 — Findings cite evidence by index
**2026-09-14 · active**

**Context.** The product claim is "it explains *why*". A model that paraphrases its
sources cannot be checked, and a paraphrase that drifts is indistinguishable from a
fabrication.

**Decision.** `risk.py` numbers the evidence `[0]`, `[1]`, `[2]`… and the model returns
`evidence_indexes`. We map those back to the real `Evidence` objects before storing.

**Consequence.** Every finding in the UI links to a real Slack message or Linear issue.
The model structurally cannot invent a source. Cost: findings can only cite evidence
that was collected in that run.

---

## ADR-0004 — Findings and actions come from the latest completed run
**2026-09-14 · active**

**Context.** Each `/sync` inserts a new set of findings. Reading all rows for a project
meant the dashboard counts climbed on every sync — two syncs turned 2 blockers into 4.

**Decision.** `_latest_run_ids()` finds the most recent completed run per project (one
query, no N+1) and findings/actions are filtered to it. Older rows stay as history.

**Consequence.** A re-sync replaces the dashboard state instead of accumulating.
`agent_runs` is the history; `findings` is the current picture. Covered by
`test_resync_replaces_the_previous_findings`.

---

## ADR-0005 — Claude with typed output, isolated in one file
**2026-09-14 · active**

**Context.** Loose JSON parsing from an LLM is the most common source of runtime
breakage in agent code.

**Decision.** `claude-opus-5` via `client.messages.parse(output_format=PydanticModel)`.
Every LLM call goes through `app/ai/llm.py`; no other file imports `anthropic`.
The model id is `LLM_MODEL` in `.env`.

**Consequence.** No `json.loads`, no try/except around model formatting. Swapping the
provider or model touches one file.

---

## ADR-0006 — GitHub remote over HTTPS, not SSH
**2026-09-14 · active**

**Context.** `git@github.com` returns `Permission denied (publickey)` — the local key at
`~/.ssh/id_ed25519.pub` is not registered on the `emon22830` account, and the `gh` token
lacks `admin:public_key` to add it.

**Decision.** `origin` is `https://github.com/emon22830/RescueAI.git`, authenticated
through the already-logged-in `gh` CLI.

**Consequence.** Push works with no further setup. To move to SSH later: register the key
on GitHub, then `git remote set-url origin git@github.com:emon22830/RescueAI.git`.

---

## ADR-0007 — A missing credential skips one app; an API error fails the run
**2026-09-14 · active**

**Context.** Six integrations, and a team may have connected three of them. If a blank
`GMAIL` credential raised, one unconnected app would 503 the whole analysis and the
other five would never run. The opposite mistake is worse: swallowing a 401 or a
rate-limit and returning `[]` makes a broken integration look like a quiet workspace.

**Decision.** The two cases are separated in every `collect_evidence`:
- **No credential in `.env`** → log a warning naming the variable, return `[]`.
  The app is not connected; the Connections page already says credentials live there.
- **Any API error** → raise. Nothing is caught. A 401, a 429 or a bad channel id
  surfaces as a failed run with the real reason.

`execute_action` does not get the same latitude — it calls `settings.require(...)` and
raises, because a human approved a write and a silent no-op would be a lie. The
executor records that failure per action in `approve_actions`.

**Consequence.** A partial setup still produces findings from the apps that are wired
up. `test_analysis_runs_with_no_evidence` keeps passing with an empty `.env`.

---

## ADR-0008 — One Google token module, not three copies
**2026-09-14 · active**

**Context.** Gmail, Drive and Calendar are three APIs behind a single OAuth client and
one refresh token. The exchange is the same fifteen lines in all three.

**Decision.** `integrations/google_auth.py` holds `access_token()`, `headers()` and
`is_connected()`, and nothing else. It caches the token until a minute before it
expires, so one analysis mints it once rather than six times.

**Consequence.** This is not the start of an integration framework — there is no base
class, no registry, and each of the three files still builds its own requests, parses
its own responses and maps its own `Evidence`. If a fourth Google API is ever added it
imports this and nothing more. See [[adr-0001]].

---

## ADR-0009 — The project state is written by the risk node, not a fourth agent
**2026-09-14 · active**

**Context.** The analysis flow calls for a "generate project state" step: a health
verdict, a short summary, and progress where it can be measured. The obvious shape is a
fourth node with its own prompt, between `risk` and `recovery`.

**Decision.** `risk` produces it, in the same LLM call that produces the findings.
`_RiskReport` gained `summary` and `progress`; the prompt gained a second half that asks
for them after the findings.

**Consequence.** `agent-rules.md` still holds — only `risk` and `recovery` call the LLM,
and an analysis still costs two calls rather than three. The project state is grounded in
exactly the evidence pass that produced the findings, so the summary cannot contradict
the findings sitting next to it on screen. The cost is that `risk.py` now does two things
and its docstring has to say so. If a future summary needs evidence `risk` does not see,
that is the signal to split it out.

**Progress is nullable on purpose.** The model is told to return null unless the evidence
measures completion — closed vs. open issues, milestones shipped. A percentage nobody can
check is worse than no percentage, and this product's whole claim is that every number on
screen traces back to something real.

---

## ADR-0010 — Project state is stored on the run, not recomputed on read
**2026-09-14 · active**

**Context.** `_summaries_for` used to recompute health from the severities of the stored
findings on every read. That worked while health was a pure function of severities, and
stops working the moment the agent also writes a summary and a progress number, which
cannot be re-derived from anything.

**Decision.** `agent_runs` gained `health`, `summary`, `progress` and `activity`, written
when the run completes. Reads return what the agent concluded on that run. Only the
blocker and risk *counts* are still tallied on read, from that same run's findings.

**Consequence.** A run is now a complete record of one investigation, which is what makes
the run history worth showing. `health_for()` survives as the fallback for a run written
before the column existed, so old rows still answer correctly. The health rule itself
lives in one place — `agents/state.py` — and both the node and the service call it.

---

## ADR-0011 — `sync` and `analyze` run the same work, separated by `triggered_by`
**2026-09-14 · active**

**Context.** `POST /sync` is meant to "retrieve fresh information from connected
applications and update the project state". That is, exactly, what `POST /analyze` does.
The temptation is to invent a difference — an incremental collection, a cheaper pass.

**Decision.** Both call `analyze_project()`. The only difference is the `triggered_by`
value stored on the run: `"analyze"` or `"sync"`. There is no incremental mode.

**Consequence.** Two endpoints, one code path, no second workflow to keep in step. The
run history still tells a user which button produced which state. Every integration
fetches a bounded recent window anyway, so a "full" re-collection is cheap enough that an
incremental one would be complexity bought for nothing. If re-collection ever becomes
slow, the fix is a background job, not a second kind of analysis.

---

## ADR-0012 — An unknown project id is a 404 on every path, never an empty list
**2026-09-14 · active**

**Context.** `/findings`, `/runs` and `/actions` short-circuited to `[]` when a project
had no completed run. A typo in the id produced the same empty list as a project that had
genuinely been analyzed and found clean — the two are opposite facts.

**Decision.** All three call `_ensure_project_exists()` first, which raises
`ProjectNotFound` and becomes a 404 through the handler already in `main.py`. An empty
list now means one thing only: this project exists and has nothing to show yet.

**Consequence.** One extra cheap `select id` per read. Worth it — the frontend can tell
"nothing found yet" from "you are looking at a project that does not exist", and so can
anyone debugging with curl.

---

## ADR-0013 — Gemini replaces Claude as the LLM, at the same single boundary
**2026-09-14 · active**

**Context.** The project needs an LLM for exactly two nodes, `risk` and `recovery`, and
this is a hackathon with no budget. The Anthropic API has no free tier; the Gemini API
does. The locked stack named `anthropic 1.5.0` and `claude-opus-5`.

**Decision.** `google-genai` replaces `anthropic`, and `gemini-3.8-flash` replaces
`claude-opus-5` as the `LLM_MODEL` default. The credential is `GEMINI_API_KEY`. The swap
touches `app/ai/llm.py` and nothing else in the application: `ask` and `ask_for` keep
their exact signatures, so `risk.py` and `recovery.py` are unchanged, and the 60 tests
passed with `anthropic` uninstalled from the venv.

**Consequence.** Structured output moves from `client.messages.parse(output_format=...)`
to `generate_content(config=GenerateContentConfig(response_schema=...))`, which returns
the same validated Pydantic object via `response.parsed`. Two Gemini-specific hazards are
handled in `llm.py`: thinking tokens are drawn from the output budget, so
`thinking_budget` is capped to leave room for the answer; and `response.parsed` is `None`
rather than an exception when the model returns nothing usable, so `ask_for` raises
`LLMError` and the run is recorded as failed instead of silently producing no findings.

The free tier has real rate limits, and the graph makes two LLM calls per analysis. A
demo that re-analyzes repeatedly can hit them. If that becomes a problem the answer is a
paid key or a smaller model, not caching — a cached analysis is a lie about the present.

**This ADR is what authorizes the change to the locked stack in `02-stack.md`.**

---

## ADR-0014 — Google is granted per project, not configured per deployment
**2026-09-14 · active**

**Context.** Slack, Linear and GitHub moved to per-project credentials, but Gmail, Drive
and Calendar stayed on one `GOOGLE_REFRESH_TOKEN` in `backend/.env` — deferred as
"Phase 2". That is a shared mailbox: every project in the deployment read the same
Gmail, and a second customer would have read the first one's mail. For a product where
each project is somebody else's workspace, that is not a deferral, it is a data leak.

**Decision.** `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` stay in `.env` — they
identify the *application* to Google, the same way the Supabase Auth Google provider is
configured once. `GOOGLE_REFRESH_TOKEN` is deleted. Each project grants its own access
through a consent flow started from its Connections page, and the refresh token it gets
back is Fernet-encrypted into the same `integrations` table the token apps use.

One row, `provider = 'google'`, serves all three apps: Gmail, Drive and Calendar are
three APIs behind a single Google consent, so three rows would mean three things to
revoke and three ways to disagree.

**Consequence.** `collect_evidence(project_id, project_name)` is now genuinely uniform
across all six integrations — the `# noqa: project_id unused` markers are gone, and
`google_auth` caches an access token per project instead of one globally.

The consent round trip leaves the app, so the callback cannot carry a bearer token. It
proves itself with a Fernet-signed `state` carrying the project and owner, expiring in
ten minutes; `security.py` remains the only file that touches Fernet. `access_type=
offline` with `prompt=consent` is mandatory on the authorize URL — without both, a user
who has already consented gets no refresh token and the connection dies silently an hour
later.

Cost: connecting Google is now a redirect, not a form, and `BACKEND_URL` must match the
redirect URI registered on the OAuth client exactly or Google refuses the round trip.

---

## ADR-0015 — An analysis is accepted, not awaited
**2026-09-14 · active**

**Context.** `POST /analyze` ran the whole graph inside the request: six external APIs,
then two LLM calls. Against stubs that is a few milliseconds; against a real workspace
with Slack history, a Drive export and a Linear query it is minutes, and every proxy and
browser between the user and the app has an opinion about a request that long. The
synchronous design also meant a crash surfaced as a bare 500, and the run row it left
behind said `running` forever.

**Decision.** The request writes the run as `queued` and returns **202** with it. The
work happens afterwards — from a FastAPI `BackgroundTasks` for a user-triggered run, or
from the scheduler for a timed one. `start_analysis` (checks ownership, writes the row)
and `run_analysis` (does the work, no ownership check — the row is proof it was already
checked) are the two halves. The run row is the handle: the frontend polls `/runs` until
its status leaves `queued`/`running`.

**Consequence.** A failure is now recorded *on the run* — `status: failed`, `error`,
`completed_at` — and notified, rather than raised at a caller who has already left. That
is the only correct behaviour for a scheduled run, where there is no caller at all.

Four tests changed to match: `/analyze` returns 202 with a queued run, and the finished
run is read back from `/runs`. TestClient runs background tasks before returning the
response, so tests read the completed run on the very next call with no waiting.

`status` gained `queued` and `triggered_by` gained `schedule`, both as check-constraint
changes in migration 0002. `AgentRunResponse` and the frontend's `AgentRun` mirror them.

Cost: the UI is now a poller. `ProjectPage` re-reads every 3s while a run is in flight
and stops when it is not, and anything that renders a run must handle a run with no
counts yet — `LatestAnalysis` used to label anything not failed as "Completed", which
would have been a lie about a queued run.

---

## ADR-0016 — The scheduler is one in-process loop, not a queue
**2026-09-14 · active**

**Context.** A tool that only looks when somebody clicks is not monitoring anything. The
product promise is that it tells you your project is on fire; that requires it to run
while nobody is watching. The obvious answers — Celery, RQ, APScheduler, a cron service
— all mean a broker, a worker process and a deployment topology, against a hard rule in
`CLAUDE.md` that says no extra layers and a junior must be able to follow any file.

**Decision.** One `asyncio` task, started and stopped by the FastAPI lifespan, in
`app/scheduler.py`. Each tick asks `service.due_projects()` what is due and runs each one
to completion in a worker thread (`asyncio.to_thread`) — the whole analysis path is
blocking, so running it on the event loop would freeze every request while a project is
analysed. Projects run one after another, not fanned out, because a tick that hits every
integration at the same minute is how a rate limit gets found.

**Consequence.** No new dependency, no second process, one file to read. The cost is
honest and written at the top of that file: **this holds for a single instance only.**
Two processes would both pick up the same due project. `SCHEDULER_ENABLED=false` turns
it off on a second instance, and the day this needs to scale, that file is where a lock
or a real queue goes.

`due_projects` also skips any project with a `queued` or `running` run. Without that, an
analysis that takes longer than its own interval would stack runs on itself — and on a
database where `last_synced_at` cannot be written, it would run every single tick.

The floor is 15 minutes (`MIN_SYNC_MINUTES`). Below that costs more in API calls than it
buys in freshness; nothing in Slack or Linear changes meaningfully in ten minutes.

---

## ADR-0017 — A changed verdict is told in the app, never posted to Slack
**2026-09-14 · active**

**Context.** Monitoring is only useful if somebody hears the result. The natural place
to put "your project is now At risk" is the Slack channel the team already watches — and
the project already holds a Slack token with `chat:write` for exactly that.

**Decision.** Notifications are in-app only: a row in `notifications`, a bell in the app
shell. Nothing is posted to a connected workspace.

**Consequence.** This is `CLAUDE.md`'s "nothing writes to an external app without human
approval" applied to ourselves. An alert is a write, and a per-project "notify me in
Slack" toggle would be standing approval for a message whose contents nobody has seen —
which is precisely what the approval gate exists to prevent. The recovery plan can still
*propose* `slack/post_message`, and a human still approves that one by one.

Only a *change* is notified. A run that concluded the same thing as the one before it is
not news, and a notification per tick would train the user to ignore all of them. A
failed run is always notified, because a background failure nobody is told about is
indistinguishable from silence.

`_notify` can never fail the run around it: the analysis already succeeded, and losing
the alert is better than losing the result it was about. The same reasoning protects
`_touch_synced`, which is the one write a pre-migration database has no column for.

Cost: someone who does not open the app does not hear anything. An email digest is the
follow-up, and it is a write to an address the user gave us, not to a shared workspace.

---

## ADR-0018 — One catalog is the contract between planner, API and UI
**2026-09-14 · active**

**Context.** What the system can do to a connected app was written down in three places
that had no way of agreeing: the `if action.type == …` chain inside each integration, a
hand-written list in the recovery prompt, and — once the dashboard could take actions —
whatever the frontend decided to offer. The prompt already listed `slack / post_message`
for weeks before `slack.execute_action` could do it, which is exactly the failure mode:
the agent proposes a step, a human approves it, and only then does it turn out that
nothing can run it.

**Decision.** `executor.ACTION_TYPES` is the single list. Each entry carries the
integration, the type, the **verb** a project manager would use (`add`, `update`,
`delegate`, `close`, `message`), a label, what `target` means for that type, what
`params.value` means, and the guidance line for the model. The recovery prompt is
generated from it at import time; `GET /actions/types` serves it filtered to the apps a
project has connected; `execute` dispatches on it.

**Consequence.** Adding an action is one entry plus one branch in that integration —
and a test fails if you forget the branch. `test_every_catalogued_action_type_is_
actually_dispatchable` calls every catalogued type with empty arguments and fails on
`NotImplementedError` specifically; anything else means the type was recognised and then
refused on its arguments, which is correct. A second test asserts the prompt contains
every catalogued type. Verified by deliberately adding a bogus entry and watching both
fail.

Executor was the right home: it is already the module that maps an action to an
integration, so knowing what each accepts is its existing job, not a new layer.

Cost: `executor` now imports pydantic and `recovery` imports `executor`. The import
graph stays acyclic because the integrations' dependency on `service` is lazy.

---

## ADR-0019 — A user can act without the agent proposing it first
**2026-09-14 · active**

**Context.** Every action had to originate in a recovery plan. A manager who can already
see that the payments channel needs telling had to run an analysis, wait for the agent
to happen to propose that step, and then approve it. For the apps the product is built
around — an issue tracker and a chat tool — that is a worse experience than the tools
themselves.

**Decision.** `POST /projects/{id}/actions` creates an action a person wrote and runs it
in the same request. Writing it *is* the approval: the user chose the app, the target
and the words, and pressed a button that named what it would do. There is no second
human left to ask.

It is deliberately **not** a separate execution path. The row is inserted as `pending`,
goes through the same `_approve`, and reaches the same `executor.execute` guard that
refuses anything not `approved`. `origin` (`agent` | `user`) records which of the two
wrote it, and the UI says "You" or "Agent" on every result.

**Consequence.** `actions.run_id` becomes nullable — a dashboard action may exist before
the project has ever been analysed. That in turn changes `get_actions`, which now
returns the latest run's plan *plus* every action with no run, so a manual action
survives a re-sync instead of disappearing with the run it was contemporary with.

The composer only offers what the project has connected, because offering an app that
will certainly fail is worse than offering nothing. An unknown type or an unconnected
app is a 400 with the reason, not a 500.

This does not weaken [[adr-0017]] or the rule it comes from. Nothing writes to an
external app without a human deciding: the difference is only whether the human is
approving a sentence the model wrote or one they wrote themselves.

---

## ADR-0020 — What a team built and what its plan says are different agents
**2026-09-14 · active**

**Context.** `engineering` read GitHub *and* Linear. Adding Jira, Asana and Trello would
have made it a five-app node, and the node's own question — "what has actually been
built?" — is not the question a task tracker answers. A tracker says what somebody
*intends*; commits say what exists.

**Decision.** A fourth investigator, `delivery`, reads every tracker — Linear, Jira,
Asana, Trello. `engineering` keeps GitHub alone. `requirements` gains Notion beside
Drive and Calendar.

**Consequence.** The gap this product exists to find — the plan says shipped, the repo
says nothing has landed — now has the two halves collected by different agents and
logged as different lines in the run's activity. A user reading the log sees "delivery:
4 items, engineering: 0 items" and has learned something.

Four nodes fan out in parallel where three did, so a project connecting a tracker and a
repo collects them concurrently rather than one after the other.

It moves `Linear` out of `engineering`, which changed the agent names in the activity
log. The tests that asserted those names now derive them from `supervisor.AGENTS`, and
the ones that counted six apps derive from `executor.INTEGRATIONS` — so the next
connector does not mean editing assertions by hand.

---

## ADR-0021 — Four trackers, because a team only uses one
**2026-09-14 · active**

**Context.** The product assumed Linear. Linear is a startup tool; most of the industry
runs Jira, and plenty of teams run Asana or Trello instead of either. A rescue tool that
cannot read the tracker a team actually uses cannot see the plan at all, which is half
its evidence.

**Decision.** Jira, Asana and Trello alongside Linear, plus Notion beside Drive for
specs. All four are token apps on the existing per-project model — no new environment
variable, no shared credential, nothing in `.env`.

**Consequence.** Three shapes that are easy to get wrong and invisible until a live
token is in play, each now pinned by a test:

- **Jira's search endpoint moved.** `/rest/api/3/search` was deprecated in May 2025 and
  fully removed by the end of October 2025; it is `/rest/api/3/search/jql`, paging on
  `nextPageToken`, and it returns *only* an id and a key unless `fields` is passed
  explicitly. Code written from memory against the old endpoint collects nothing and
  says nothing about why.
- **Jira's text is not text.** The v3 API speaks Atlassian Document Format, so a
  description read back is a tree and a comment sent is a tree. `_adf` and `_adf_text`
  are the two ends of that.
- **Jira has no settable status.** Closing is a transition, and which transition means
  closed is a per-workflow question — so a named one wins and otherwise the first one
  into the `done` status category is used.

Trello authenticates with a pair. Its API key identifies the application rather than the
user and Trello's own docs ship it in client-side code, so it is stored as metadata like
`repo` or `site`; the token beside it is the secret half and is encrypted like every
other credential. That distinction is now written into `integration-rules.md`, because
the next app with two credentials may not split the same way.

Asana's own task search is a paid feature, so collection finds the Asana *project* by
typeahead and then reads that project's tasks. Typeahead is explicitly "fast, not
exhaustive" in Asana's docs — fine for locating a project, not fine for collecting the
evidence itself.

Notion only returns pages its integration has been shared with, so an empty result
usually means nobody added it to the page. That is what the log now says, rather than
leaving it to look like the project has no spec.

---

## ADR-0022 — The test suite may not touch the real database
**2026-09-14 · active**

**Context.** `conftest.py`'s `db` fixture was opt-in. Tests that did not ask for it —
`test_graph.py`, among others — ran against whatever `service.get_db()` returned, which
with a filled-in `backend/.env` is the live Supabase project. It went unnoticed while
every integration was unimplemented. Adding four connectors that each look up a stored
credential made it four more live queries per test, and the suite's runtime jumped from
1.1s to 2.7s.

**Decision.** The `db` fixture is `autouse=True`. Every test gets a fresh in-memory
database whether it asks for one or not; the ones that need to inspect it still request
`db` and get the same instance.

**Consequence.** The suite is hermetic and runs in 0.4s. More importantly, a test can no
longer read or write the real project's data by forgetting a fixture — which was a real
risk the moment an integration test touched a write path.

---

## ADR-0023 — One Supabase client per thread, not one per process
**2026-09-14 · active**

**Context.** `get_db()` was `@lru_cache`, so the whole process shared one client. FastAPI
runs every `def` endpoint in a worker thread, and the project page opens seven requests
at once — so seven threads drove one `httpx` client. Supabase speaks HTTP/2, so those
requests were multiplexed over a single TCP connection whose read loop is not safe to
drive concurrently. Whichever request lost raised `httpx.ReadError`, nothing handled it,
and a page whose data was perfectly fine rendered as "Project unavailable".

This is the cause behind the 500s that were chased for most of a day. Two earlier
theories — a CORS misconfiguration, then a `CREDENTIAL_ENCRYPTION_KEY` mismatch — were
both wrong, and both looked plausible because the failure never reached the browser as a
500 (see [[adr-0024]]).

**Decision.** `get_db()` keeps the client in `threading.local()`. One client per worker
thread, created on first use.

**Consequence.** A handful of extra connections instead of one, in exchange for removing
the sharing entirely. `lru_cache` must not come back here — it reads as a harmless
memoisation and is the bug. An `HTTPError` handler in `main.py` now names a dropped
connection if one ever happens, rather than letting it read as a crash.

---

## ADR-0024 — An unhandled error is answered inside the CORS layer
**2026-09-14 · active**

**Context.** Starlette builds its stack as `ServerErrorMiddleware` → user middleware →
`ExceptionMiddleware`. An exception no handler claims is turned into a 500 by the
outermost middleware — outside `CORSMiddleware` — so the response carries no
`access-control-allow-origin`. The browser refuses to surface it and `fetch` rejects,
which is indistinguishable from the backend being down. A backend that crashed on one
endpoint therefore read in the UI as a backend that was unreachable, and sent two
separate investigations after the wrong cause.

Registering `@app.exception_handler(Exception)` does **not** fix this: that handler is
installed on `ServerErrorMiddleware`, still outside CORS. Verified both ways.

**Decision.** A `@app.middleware("http")` catch-all registered *before* the CORS
middleware, so CORS ends up outside it and can stamp its headers on what we return. It
logs the traceback and answers a real `{"detail": ...}`.

**Consequence.** Order of registration in `main.py` is load-bearing: the last middleware
added is the outermost, so CORS must be added *after* the catch-all. A regression test
asserts a 500 still carries `access-control-allow-origin`, and it was checked to fail
when the middleware is removed.

---

## ADR-0025 — A production build fails when its client variables are missing
**2026-09-14 · active**

**Context.** `supabaseClient.ts` throws at module top level when `VITE_SUPABASE_URL` or
`VITE_SUPABASE_ANON_KEY` is missing. A production build replaces `import.meta.env.VITE_*`
with `undefined` *before* minifying, so that throw becomes provably unconditional and
every module downstream of it is dead code — which is the entire app. The build exits 0
and emits a plausible bundle about a third the normal size (262 kB against 581 kB). What
deploys is a white screen, and nothing in the output reads as a failure.

Found by building a clean clone: same 132 modules transformed, half the output, not one
app string in the bundle.

**Decision.** `vite.config.ts` refuses to build when either variable is unset. Build
only — `vite dev` still runs on a half-filled `.env`. CI additionally greps the emitted
bundle for `createClient`, `refreshSession` and `RescueAI`.

**Consequence.** A misconfigured Vercel project now fails its build loudly instead of
deploying an empty app. The bundle check is deliberate redundancy: the guard covers the
known path to an empty bundle, the grep covers any other.

---

## ADR-0026 — Dependencies are pinned, and Dependabot proposes the moves
**2026-09-14 · active**

**Context.** `backend/requirements.txt` named ten packages and pinned none. CI and Render
each resolved the tree independently, so a breaking major release could deploy itself
with no commit from anyone, and a passing suite proved nothing about the versions
production would run.

**Decision.** Exact pins on the direct dependencies, verified by building a fresh venv
from the file alone and running the suite against it. Transitives still float — a full
lock would be more reproducible and more machinery than this project wants.

**Consequence.** Nothing updates on its own any more, including a security release. That
is the point of pinning and it is also how a project silently falls a year behind, so
`.github/dependabot.yml` opens weekly grouped pull requests for pip, npm and the actions
themselves; CI runs the suite against each, and the green check is the evidence for
merging. Upgrading is now: change a pin, run the tests, commit.

---

## ADR-0027 — CI gates pull requests; the deploy is still ungated
**2026-09-14 · active**

**Context.** Render and Vercel both redeploy on their own when `main` moves. Adding CI
does not change that — the checks run *in parallel* with the deploy, so a red build
still ships. Making the checks a real gate means turning auto-deploy off on each service
and triggering it from the workflow instead; doing only half of that deploys everything
twice.

Required status checks can only pass *after* a commit exists, so enforcing them on
direct pushes makes direct pushes impossible — it forces a pull request for every
change. For a single maintainer mid-build that is a real tax for little gain.

**Decision.** `main` is protected with **Backend tests** and **Frontend build** as
required checks, must-be-up-to-date on, force-push and deletion refused, and
`enforce_admins` **false**. The workflow's `deploy` job is inert until
`RENDER_DEPLOY_HOOK_URL` or `VERCEL_DEPLOY_HOOK_URL` exists.

**Consequence.** Be honest about what this buys: the checks gate pull requests, not the
maintainer's own pushes, and the deploy is not gated at all. Force-push and deletion
protection are absolute. Turn `enforce_admins` on the moment a second person has write
access, and add the hooks when the deploy should wait for green.

One thing it already earned: `secrets` is not a context an `if` expression can read at
any level, so `if: ${{ secrets.X != '' }}` does not evaluate false — it fails the whole
workflow to parse. The first run caught that in zero seconds. Map secrets to `env` on
the job and test `env.X`.

---

## ADR-0028 — A verified token is remembered for a minute
**2026-09-14 · active**

**Context.** `get_current_user` verifies every bearer token with a network round trip to
Supabase Auth. One screen opens seven requests, so seven hops happened before any of
them looked at a project.

**Decision.** A successful verification is held in-process for 60 seconds, keyed by the
token, under a lock, with expired entries swept on write.

**Consequence.** A Supabase access token is a JWT already valid for an hour on its own
terms, so remembering a good one for a minute extends nobody's access — it only stops us
asking the same question seven times a second. **Only successes are cached**: a rejection
is re-asked every time, so a session that has just been renewed is never told it is still
invalid. The cache is per-process, so a second instance verifies independently.
