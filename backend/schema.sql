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

create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  status text not null check (status in ('running', 'completed', 'failed')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  evidence_count int,
  finding_count int,
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

create table if not exists actions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  run_id uuid not null references agent_runs(id) on delete cascade,
  integration text not null check (
    integration in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar')
  ),
  action text not null,
  description text not null,
  params jsonb not null default '{}',
  status text not null default 'pending' check (status in ('pending', 'executed', 'failed')),
  result text,
  approved_at timestamptz,
  executed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists agent_runs_project_idx on agent_runs (project_id, started_at desc);
create index if not exists evidence_run_idx on evidence (run_id);
create index if not exists findings_run_idx on findings (run_id);
create index if not exists actions_run_idx on actions (run_id, status);
