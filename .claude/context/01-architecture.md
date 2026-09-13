---
doc: architecture
version: 1
updated: 2026-09-14
status: active
---

# Architecture

## Layer discipline

```
React        UI only — never calls an external API directly
   ↓
FastAPI      HTTP, validation, coordination — thin
   ↓
LangGraph    orchestration only — NOT the database
   ↓
Integrations Slack · Gmail · Drive · Linear · GitHub · Calendar
   ↓
Supabase     memory: projects, syncs, evidence, findings, actions
```

Two ways to get this wrong, both fatal to readability: letting LangGraph state become the
database, and letting React talk to the external apps.

## The workflow

```
START
  ↓
supervisor
  ├──────────────┬──────────────┐
  ↓              ↓              ↓
communication  engineering  requirements
Slack+Gmail    GitHub+Linear  Drive+Calendar
  └──────────────┴──────────────┘
                 ↓
               risk          cross-references everything → findings
                 ↓
             recovery        findings → a plan
                 ↓
          (stored as pending, human approves)
                 ↓
             executor        writes back. No LLM.
```

The three investigators run in parallel. `AgentState["evidence"]` is
`Annotated[list[Evidence], operator.add]` so they append instead of overwriting. `risk`
has an edge from all three, so LangGraph waits for all of them before it runs.

## Request flow

```
POST /projects/{id}/analyze
  → api/analysis.py
  → projects/service.py        creates an agent_runs row
  → agents/graph.py            runs the workflow
  → integrations/*             real API calls
  → ai/llm.py                  risk + recovery reasoning
  → projects/service.py        saves evidence, findings, actions
  → agent_runs marked completed
```

Approval is two separate endpoints (`/analyze` then `/actions/approve`), not a LangGraph
`interrupt()`. The pause lives in the database as `status = "pending"`, which survives a
server restart and needs no checkpointer.

## Folder responsibilities

| Folder | Owns |
|---|---|
| `api/` | HTTP only — parse, validate, delegate, return |
| `projects/` | project business logic and persistence |
| `agents/` | the graph and its nodes |
| `integrations/` | one file per external app; `collect_evidence` and `execute_action` |
| `ai/` | the only place that talks to an LLM |
| `db/` | the Supabase client |

Do not rename these into abstract architecture terms.
