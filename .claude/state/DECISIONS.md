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
