# Authentication

Everything about *who is calling* lives in this folder. Three files:

| File | Answers |
|---|---|
| `dependencies.py` | Is this request from a signed-in user, and which one? |
| `security.py` | How are a project's third-party tokens kept safe at rest? |
| `router.py` | `GET /auth/me` — the one auth endpoint the API exposes. |

## We do not store users

Supabase Auth owns identity: sign-up, sign-in, password hashing, session tokens,
expiry and refresh. There is **no users table of ours**, no password field anywhere in
`schema.sql`, and no login endpoint on this server — a login route here would mean this
server handling passwords, which is exactly the part worth not owning.

What this folder adds is the half Supabase cannot do for us: turning the token the
browser was given into a user id, and making sure that id is checked against every row
before it is returned.

## The request path

```
Browser                          Backend                        Supabase
   |                                |                              |
   | supabase.auth.signIn ----------|----------------------------> |
   | <-------------------------------------- access_token -------- |
   |                                |                              |
   | GET /projects                  |                              |
   | Authorization: Bearer <token>  |                              |
   | -----------------------------> |                              |
   |                                | auth.get_user(token) ------> |
   |                                | <------------- user.id ----- |
   |                                |                              |
   |                                | service.list_projects(user.id)
   |                                |   WHERE owner_id = user.id   |
   | <-------- only this user's projects ----------------------- |
```

1. The frontend signs in against Supabase directly
   (`frontend/src/lib/supabaseClient.ts`).
2. `frontend/src/lib/api.ts` attaches the session's `access_token` as
   `Authorization: Bearer …` to **every** request. A `fetch` anywhere else is a bug.
3. `get_current_user` verifies that token and returns `CurrentUser(id, email)`.
4. An invalid, expired or missing token raises `AuthError`, which the handler in
   `app/main.py` turns into **401**. No route writes its own try/except.

## Ownership is application code, not Postgres

This is the part worth reading twice.

The backend talks to Supabase with the **service key**, which *bypasses row-level
security by design* — it has to, because the agent writes rows on behalf of a user it
is not authenticated as. So RLS will not protect anything here. Ownership is enforced
in `app/projects/service.py`, on every single call, by `_ensure_owned(project_id,
owner_id)`.

The contract that keeps that honest:

- Every route that touches a project depends on `get_current_user`.
- Every service function takes `owner_id` and checks it before returning a row.
- A project that exists but belongs to someone else raises the same `ProjectNotFound`
  as one that never existed — **404, never 403**. A 403 would confirm that a project id
  is real, which is a membership oracle.

`tests/test_auth.py` holds that line: it is the only test file that exercises the real
Supabase verification path, and it asserts the 404-not-403 behaviour directly.

## The second kind of secret

`security.py` is not about users — it is about the credentials *users connect*.

RescueAI is multi-tenant: every project connects its own Slack, Linear and GitHub
tokens, so those cannot live in `backend/.env`. They live in the `integrations` table,
encrypted with Fernet under `CREDENTIAL_ENCRYPTION_KEY`, and `encrypt`/`decrypt` here
are the only code that touches them.

It also signs the OAuth `state` for Google. That round trip leaves our app entirely, so
the state coming back has to prove it is the one we sent: `sign_state` packs the claims
into a tamper-proof string with a 10-minute TTL and `verify_state` rejects anything
forged, altered or stale as a `StateError` — an `AuthError` subclass, so it answers 401
like any other caller who cannot prove who they are.

Nothing on any path ever returns a credential value. The integrations API returns a
provider name, a boolean, and what the app said about itself when the token was
verified — never the token.

## Seeing it

`GET /auth/me` returns the caller's id and email, or 401. The bearer scheme is declared
(`bearer_scheme` in `dependencies.py`), so every protected route shows a padlock in
`/docs` and the **Authorize** button there takes a real session token.
