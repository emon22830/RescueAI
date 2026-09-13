-- Run this once in the Supabase SQL editor.

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  goal text not null,
  created_at timestamptz not null default now()
);

create table if not exists integrations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  provider text not null check (
    provider in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar')
  ),
  connected boolean not null default false,
  created_at timestamptz not null default now(),
  unique (project_id, provider)
);

-- A run holds the project state the agent produced: health, summary and progress.
-- They are stored, not recomputed on read, so the dashboard shows what the agent
-- actually concluded on that run. `activity` is the agent's own log of which app
-- returned what, which is how a user sees that Gmail contributed nothing.
create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  status text not null check (status in ('running', 'completed', 'failed')),
  triggered_by text not null default 'analyze' check (triggered_by in ('analyze', 'sync')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  evidence_count int,
  finding_count int,
  health text check (health in ('on_track', 'watch', 'at_risk')),
  summary text,
  progress int check (progress between 0 and 100),
  activity jsonb not null default '[]',
  error text
);

create table if not exists evidence (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  run_id uuid not null references agent_runs(id) on delete cascade,
  source text not null check (
    source in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar')
  ),
  type text not null,
  title text not null,
  content text not null,
  url text,
  "timestamp" timestamptz,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists findings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  run_id uuid not null references agent_runs(id) on delete cascade,
  title text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  confidence real not null check (confidence between 0 and 1),
  description text not null,
  evidence jsonb not null default '[]',
  created_at timestamptz not null default now()
);

-- One step of a recovery plan. `status` is its whole life: proposed by the agent,
-- approved by a human, running, then completed or failed. Nothing is sent to an
-- external app in any other state, and the app's own answer is kept in `result`.
create table if not exists actions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  run_id uuid not null references agent_runs(id) on delete cascade,
  integration text not null check (
    integration in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar')
  ),
  type text not null,
  description text not null,
  target text not null default '',
  reason text not null default '',
  params jsonb not null default '{}',
  status text not null default 'pending' check (
    status in ('pending', 'approved', 'executing', 'completed', 'failed')
  ),
  result text,
  approved_at timestamptz,
  executed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists agent_runs_project_idx on agent_runs (project_id, started_at desc);
create index if not exists evidence_run_idx on evidence (run_id);
create index if not exists findings_run_idx on findings (run_id);
create index if not exists actions_run_idx on actions (run_id, status);
