# Open blockers

Resolved items move to CHANGELOG.md. Never delete one silently.

## 1 — No Supabase credentials (blocks everything that persists)

Every endpoint except `/health` returns **503** with the list of missing variables.
That is correct behaviour, not a bug.

**Unblocks when:** a Supabase project exists, `backend/schema.sql` has been run in its
SQL editor, and `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are in `backend/.env`.

**Untested until then:** whether the schema applies cleanly and whether PostgREST
returns the column names the service expects.

## 2 — No demo data in the real apps

The agent is only as good as what it can find. The "SaaS Product Launch" scenario —
the Slack thread about the blocked payment API, the requirements-change email, spec v3
in Drive, overdue PAY-124 in Linear, the launch review in Calendar — has to exist in
real connected workspaces before any demo is possible.

**Never solve this by hardcoding data in source.** See [[adr-0002]].

## Traps worth knowing

- `.env` is gitignored and the repo is **public**. Check before every push.
- SSH to GitHub fails (`Permission denied (publickey)`) — the key at
  `~/.ssh/id_ed25519.pub` is not registered on the account. The remote uses HTTPS
  through the `gh` CLI instead. See [[adr-0006]].
- `postgrest.APIError` is what the Supabase client raises; it is handled globally in
  `main.py`. Do not catch it per route.
