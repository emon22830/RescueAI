-- Run this once, by hand, in the Supabase SQL editor for the project already connected
-- in backend/.env. It moves the existing single-tenant tables to the multi-tenant shape
-- now in schema.sql — schema.sql itself won't touch them, because every statement there
-- is `create table if not exists` and these tables already exist.
--
-- Checked before writing this: the live project has exactly one row in `projects`
-- ("SaaS Product Launch"), one in `agent_runs`, and zero in `integrations` — so nothing
-- here drops real data except the empty `integrations` table.

-- 1. Every project needs an owner. Nullable for now: there is no signed-up user yet to
--    assign the existing project to, and this must not break while that is true.
alter table projects add column if not exists owner_id uuid references auth.users(id) on delete cascade;
create index if not exists projects_owner_idx on projects (owner_id);

-- 2. `integrations` is rebuilt rather than migrated column by column — it has no rows
--    to lose. The old `connected boolean` is gone; a row now means a verified,
--    encrypted token exists for that project and provider.
drop table if exists integrations;

create table integrations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  provider text not null check (provider in ('slack', 'linear', 'github')),
  encrypted_token text not null,
  metadata jsonb not null default '{}',
  connected_by uuid not null references auth.users(id),
  connected_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (project_id, provider)
);

create index integrations_project_idx on integrations (project_id);

-- 3. After you've signed up your first real user (through the app's new signup page,
--    or Authentication → Users in the Supabase dashboard), give the existing demo
--    project an owner — or just delete it and create a fresh one through the app:
--
--   update projects set owner_id = '<your-auth-user-id>' where owner_id is null;
--
-- 4. Once every row in `projects` has an owner, close the gap `owner_id` was left open
--    for and require it going forward, matching schema.sql:
--
--   alter table projects alter column owner_id set not null;
