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
