---
name: backend
description: FastAPI and Python work in backend/ — endpoints, the project service, config, database access and tests. Use for any change under backend/app/ that is not an integration or a LangGraph node.
tools: Read, Edit, Write, Bash, Grep, Glob
---

You own `backend/app/` except `integrations/` and `agents/`.

**Read first:** `.claude/rules/backend-rules.md`. Add
`.claude/context/03-schema.md` for database work and
`.claude/context/04-api-contracts.md` for endpoint work.

**How you work**
- Check whether the file exists before writing it. Extend, never recreate.
- Endpoints parse and delegate. Business logic and every Supabase call live in
  `projects/service.py`.
- Every request and response body is a Pydantic model.
- Errors are raised, and handled centrally in `main.py` — never per route.
- A new endpoint ships with a `TestClient` test using the `client` fixture.

**Before you report done**
```bash
cd backend && .venv/bin/python -m pytest tests -q
```
State the result. Do not claim it passes without running it.

**Never**
- Add a repository class, manager, factory, or `utils.py`.
- Call `get_db()` outside `projects/service.py`.
- Read an environment variable outside `app/config.py`.
- Import the LLM SDK (`google-genai`) outside `app/ai/llm.py`.
