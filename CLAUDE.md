# RescueAI — agent context

Read this file every session. Everything else is loaded on demand.

## What this is

An AI agent that reconstructs the real state of a project by collecting evidence from
the tools a team already uses, names blockers and risks with the evidence attached,
drafts a recovery plan, and executes it only after a human approves.

```
Collect evidence → Understand state → Detect blockers → Recovery plan
      ↑                                                      ↓
   Sync again  ←  Execute actions  ←  Human approval  ←──────┘
```

## Where you are

`.claude/state/STATE.md` answers it. A SessionStart hook loads it automatically.
If it looks stale, trust the code and say so.

## Layout

```
backend/app/
  api/            HTTP endpoints
  auth/           who is calling, and the keys protecting what they connected
  projects/       project business logic
  agents/         the LangGraph workflow and its nodes
  integrations/   one file per external app
  ai/llm.py       the ONLY place that talks to an LLM
  db/supabase.py  database client
frontend/src/
  pages/ features/ components/ lib/api.ts
```

## Hard rules

- **Hackathon, not enterprise.** No repository pattern, no managers, no factories, no
  extra layers. A junior developer must be able to read any file and follow it.
- **One LangGraph workflow.** Never a second graph, never a separate AI service.
- **All external data goes through `Evidence`.** Agents reason over normalized evidence,
  never over app-specific shapes.
- **Findings cite evidence by index.** The model never restates evidence in its own words.
- **Never fake integration data.** An unimplemented integration returns `[]`. Demo data
  lives in the real connected apps, not in our source.
- **Nothing writes to an external app without human approval.**
- **Only `ai/llm.py` imports the LLM SDK (`google-genai`).**
- **Secrets come from `backend/.env`.** Never commit one, never hardcode one.
- Keep the system runnable after every change.

## Reference index — load only when the task matches

| File | Load when |
|---|---|
| `.claude/context/00-product.md` | Deciding what to build or why |
| `.claude/context/01-architecture.md` | Changing how the pieces fit together |
| `.claude/context/02-stack.md` | Adding a dependency or checking a version |
| `.claude/context/03-schema.md` | Writing a query or changing a table |
| `.claude/context/04-api-contracts.md` | Adding or changing an endpoint |
| `backend/app/auth/README.md` | Anything about sign-in, sessions or ownership checks |
| `.claude/rules/backend-rules.md` | Writing Python |
| `.claude/rules/frontend-rules.md` | Writing React |
| `.claude/rules/ui-design-rules.md` | Styling anything — colour, type, spacing, dark mode |
| `.claude/rules/agent-rules.md` | Touching `app/agents/` |
| `.claude/rules/integration-rules.md` | Writing an integration |
| `.claude/skills/new-integration/SKILL.md` | Implementing a new external app |

## Before you finish a session

Run `/handoff`. It rewrites state so the next session — or you in six months —
starts knowing exactly where things stand.
