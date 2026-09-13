---
doc: stack
version: 1
updated: 2026-09-14
status: active
---

# Stack — LOCKED

These versions are installed and verified. Do not change one without an ADR.

## Backend — Python 3.14.5

| Package | Version | Role |
|---|---|---|
| fastapi | 0.141.1 | HTTP |
| uvicorn[standard] | 0.52.4 | server |
| pydantic-settings | 2.15.0 | env config |
| langgraph | 1.2.11 | agent orchestration |
| google-genai | 2.23.0 | LLM |
| supabase | 2.31.0 | database |
| pytest | — | tests |
| httpx | — | integration HTTP calls |

## Frontend — Node 24.16.0

| Package | Version |
|---|---|
| react / react-dom | 19.2.8 |
| vite | 8.3.0 |
| typescript | 6.0.2 |
| tailwindcss + @tailwindcss/vite | 4.3.3 |
| react-router-dom | 7.18.3 |

Tailwind 4 has no `tailwind.config.js`. It is wired as a Vite plugin, and
`src/index.css` starts with `@import "tailwindcss";`.

## LLM

`gemini-3.8-flash` via
`generate_content(config=GenerateContentConfig(response_schema=PydanticModel))`, read back
from `response.parsed`. Configured by `LLM_MODEL` in `.env`. See [[adr-0013]].

Thinking tokens are drawn from `max_output_tokens`, so `llm.py` caps `thinking_budget` to
leave room for the answer. `response.parsed` is `None` — not an exception — when the model
returns nothing usable, which is why `ask_for` raises `LLMError`.

## Adding a dependency

Only when code being written now imports it. The Google API and Slack SDKs are
deliberately absent until those integrations are implemented.

## Environment variables

All of them live in `backend/.env`, listed in `backend/.env.example`. `.env` is
gitignored and the repo is public — check before every push.
