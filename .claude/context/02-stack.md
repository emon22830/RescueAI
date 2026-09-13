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
| anthropic | 1.5.0 | LLM |
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

`claude-opus-5` via `client.messages.parse(output_format=PydanticModel)`.
Configured by `LLM_MODEL` in `.env`.

Do not use `budget_tokens` or `temperature` — both are rejected on this model. Depth is
controlled by `output_config: {effort: ...}` if it is ever needed.

## Adding a dependency

Only when code being written now imports it. The Google API and Slack SDKs are
deliberately absent until those integrations are implemented.

## Environment variables

All of them live in `backend/.env`, listed in `backend/.env.example`. `.env` is
gitignored and the repo is public — check before every push.
