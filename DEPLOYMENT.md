# Deploying RescueAI

Local setup is [README.md § 9](README.md#9--set-it-up-step-by-step). This is the delta
for running the same code against a live backend and frontend instead of localhost.
Nothing in source changes between the two — every URL is read from an env var
(`backend/app/config.py`, `frontend/src/lib/api.ts`). Deploying is setting values in two
dashboards plus two one-time external registrations.

## Live deployment

| | URL |
|---|---|
| Backend (Render) | https://rescueai-xkhy.onrender.com |
| Frontend (Vercel) | https://rescue-ai-self.vercel.app |

Both are wired to the `main` branch and redeploy on push. Backend build/start commands
on Render: `pip install -r requirements.txt` / `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
from the `backend/` root directory.

## What differs from local

| Variable | Local (`backend/.env`) | Production (Render dashboard) |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | `https://rescueai-xkhy.onrender.com` |
| `CORS_ORIGINS` | `http://localhost:5173` | `https://rescue-ai-self.vercel.app` |

| Variable | Local (`frontend/.env`) | Production (Vercel dashboard) |
|---|---|---|
| `VITE_API_URL` | empty — Vite proxies to `127.0.0.1:8000` | `https://rescueai-xkhy.onrender.com` |

Everything else (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`,
`CREDENTIAL_ENCRYPTION_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_CALENDAR_ID`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) is the same value
in both places — one Supabase project, one Google OAuth client, for both environments.
If you ever split to a separate production Supabase project, run `backend/schema.sql`
there first, then every file in `backend/migrations/` in order — `schema.sql` builds a
fresh database, and the migrations are what bring an existing one forward.

**The scheduler is in-process.** Continuous monitoring runs inside the backend process
(`app/scheduler.py`), so it only runs while the service is up, and only on one instance.
If Render ever scales this to more than one, set `SCHEDULER_ENABLED=false` on all but
one of them — otherwise both pick up the same due project and analyse it twice.

Want the live backend to also accept calls from a local frontend (testing prod data
against `npm run dev`)? Make `CORS_ORIGINS` a comma list:
`https://rescue-ai-self.vercel.app,http://localhost:5173`.

## Render — backend environment variables

Set under the service's **Environment** tab:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
GEMINI_API_KEY=AIza...
LLM_MODEL=gemini-3.8-flash
CREDENTIAL_ENCRYPTION_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_CALENDAR_ID=primary
BACKEND_URL=https://rescueai-xkhy.onrender.com
CORS_ORIGINS=https://rescue-ai-self.vercel.app
```

Render's free tier spins the service down when idle — the first request after a while
can take 30–60s. `/health` is a cheap way to wake it before a demo.

## Vercel — frontend environment variables

Set under **Project Settings → Environment Variables**, scope **Production**:

```env
VITE_API_URL=https://rescueai-xkhy.onrender.com
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

`vercel.json` already rewrites every path to `/index.html` so client-side routes
(`/app/projects/:id`) don't 404 on refresh — no further Vercel config needed.

## One-time external config

These live outside both dashboards and are easy to forget after the fact — a sign-in or
Google connect that works locally and fails only in production almost always traces back
to one of these two.

**1. Google Cloud Console** (console.cloud.google.com/apis/credentials → the OAuth
client) — add a second Authorized redirect URI alongside the local one:

```
https://rescueai-xkhy.onrender.com/integrations/google/callback
```

**2. Supabase Auth** (Authentication → URL Configuration):

- Site URL: `https://rescue-ai-self.vercel.app`
- Additional Redirect URLs: `http://localhost:5173/*` and `https://rescue-ai-self.vercel.app/*`

Without both entries in the redirect list, a sign-in started on one environment bounces
back to whichever URL is set as Site URL, regardless of where the user actually is.

## CI, and gating the deploy

`.github/workflows/ci.yml` runs on every push and pull request to `main`: backend tests
(no secrets — `conftest.py` swaps Supabase for `tests/fake_db.py`), then the frontend
lint, type-check and build, then a check that the built bundle still contains the app.

That last check exists because of a failure mode worth knowing about. `supabaseClient.ts`
throws at module top level when `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` is
missing. A production build replaces `import.meta.env.VITE_*` with `undefined` before
minifying, so that throw becomes provably unconditional and **everything downstream of
it is dead code** — the entire app tree-shakes away. The build exits 0 and prints a
healthy-looking bundle about a third the normal size (262 kB instead of 581 kB), and
what deploys is a white screen. `vite.config.ts` now refuses to build without those two
variables; the bundle check in CI is the second line of defence.

`main` is protected: **Backend tests** and **Frontend build** are required checks, the
branch must be up to date before merging, and force-pushes and deletion are refused.
Administrators are exempt, which is deliberate for a single maintainer — it keeps a
direct push available when one is needed. Turn that exemption off (`enforce_admins`) the
moment a second person has write access, because until then the required checks gate
pull requests only.

Dependabot (`.github/dependabot.yml`) opens weekly grouped updates for pip, npm and the
actions themselves. Pinned dependencies do not move on their own — that is the point of
pinning — so this is what keeps a security release from waiting a year for someone to
notice it.

**Neither of those makes CI gate the deploy.** Render and Vercel each redeploy on their
own when `main` moves, in parallel with these checks, so a red build still ships. Making
the gate real is two changes per service, and both halves matter — adding the hook
without turning off auto-deploy just deploys everything twice:

1. **Render** → service → Settings → Build & Deploy: set *Auto-Deploy* to **No**, then
   create a *Deploy Hook* and save the URL as the repository secret
   `RENDER_DEPLOY_HOOK_URL`.
2. **Vercel** → project → Settings → Git: turn off automatic deployments for `main`,
   then create a Deploy Hook and save it as `VERCEL_DEPLOY_HOOK_URL`.

Repository secrets live under Settings → Secrets and variables → Actions. The `deploy`
job already reads both and skips whichever is absent, so nothing changes until you add
them.

## Verifying a deploy

```bash
# {"status":"ok","version":"0.5.0","commit":"6a6217e"} — `commit` is the build that is
# actually answering, so it is how you tell a deploy that landed from one still rolling
# out. It comes from RENDER_GIT_COMMIT, which Render sets and nothing else does, so a
# local run says "local".
curl https://rescueai-xkhy.onrender.com/health

# /health passes even when CORS is wrong, and then every screen in the app reads as
# "could not reach the backend". This is the check that catches it — a 200 with an
# access-control-allow-origin line back is correct; a 400 "Disallowed CORS origin"
# means CORS_ORIGINS on Render does not contain the Vercel URL.
curl -i -X OPTIONS https://rescueai-xkhy.onrender.com/projects \
  -H "Origin: https://rescue-ai-self.vercel.app" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization"
```

The backend logs its allowed origins once at startup (`CORS allowed origins: ...`), so
Render's deploy log says what the value actually parsed to. A trailing slash, wrapping
quotes or stray spaces are tolerated; a different hostname is not.

Then in the browser: open the Vercel URL, sign in, create (or open) a project, connect
one app, run **Analyze**. If sign-in redirects to the wrong host, re-check Supabase Auth
above. If `Analyze` fails with a CORS error in the console, re-check `CORS_ORIGINS` on
Render. If it 503s naming a variable, that variable is missing on Render, not broken —
same behavior as local, see [README.md § 12](README.md#12--troubleshooting).
