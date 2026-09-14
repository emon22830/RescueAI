-- Phase 3: the loop runs itself.
--
-- Until now an analysis only happened when somebody clicked Analyze, and it ran
-- inside the HTTP request. This migration adds the three things that turn that into
-- continuous monitoring: a per-project schedule, a queued run state so the request
-- can return before the work is done, and a notification when the agent's verdict
-- on a project changes while nobody was watching.
--
-- Safe to run on an existing database. Run it in the Supabase SQL editor.

-- 1 — every project decides how often it re-analyses itself. null means manual only.
alter table projects add column if not exists sync_interval_minutes int
  check (sync_interval_minutes is null or sync_interval_minutes >= 15);
alter table projects add column if not exists last_synced_at timestamptz;

-- 2 — a run now starts as 'queued' (accepted, not yet started) and the scheduler is
-- a third thing that can trigger one.
alter table agent_runs drop constraint if exists agent_runs_status_check;
alter table agent_runs add constraint agent_runs_status_check
  check (status in ('queued', 'running', 'completed', 'failed'));

alter table agent_runs drop constraint if exists agent_runs_triggered_by_check;
alter table agent_runs add constraint agent_runs_triggered_by_check
  check (triggered_by in ('analyze', 'sync', 'schedule'));

-- 3 — what the agent decided while the user was away. Written by the run itself,
-- read by the app's notification list. `owner_id` is denormalized from the project
-- so the list is one indexed query instead of a join per project.
create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  run_id uuid references agent_runs(id) on delete set null,
  kind text not null check (kind in ('health_changed', 'blockers_found', 'run_failed')),
  severity text not null default 'info' check (severity in ('info', 'warn', 'danger')),
  title text not null,
  body text not null default '',
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists notifications_owner_idx on notifications (owner_id, created_at desc);
create index if not exists projects_scheduled_idx on projects (sync_interval_minutes)
  where sync_interval_minutes is not null;
