-- Run this once in the Supabase SQL editor.

-- SaaS: every project belongs to the Supabase Auth user who created it. The backend
-- talks to Supabase with the service key, which bypasses row-level security, so
-- ownership is enforced in app/projects/service.py, not in Postgres policies here.
create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  goal text not null,
  -- How often the agent re-analyses this project on its own. null = manual only.
  sync_interval_minutes int check (sync_interval_minutes is null or sync_interval_minutes >= 15),
  last_synced_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists projects_owner_idx on projects (owner_id);

-- One row per project per connected app. `encrypted_token` holds a Fernet-encrypted
-- Slack/Linear/GitHub credential (see app/security.py) — never a plaintext value, and
-- never sent back to the frontend once saved. Gmail/Drive/Calendar are still one shared
-- Google OAuth app configured in backend/.env (Phase 2 moves them here too), so they
-- have no row and are reported from settings instead — see app/api/integrations.py.
create table if not exists integrations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  provider text not null check (
    -- 'google' is one row covering Gmail, Drive and Calendar: they are three APIs
    -- behind a single OAuth consent, so they share one refresh token.
    provider in ('slack', 'linear', 'github', 'google', 'jira', 'notion', 'asana', 'trello')
  ),
  encrypted_token text not null,
  metadata jsonb not null default '{}',
  connected_by uuid not null references auth.users(id),
  connected_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (project_id, provider)
);

create index if not exists integrations_project_idx on integrations (project_id);

-- A run holds the project state the agent produced: health, summary and progress.
-- They are stored, not recomputed on read, so the dashboard shows what the agent
-- actually concluded on that run. `activity` is the agent's own log of which app
-- returned what, which is how a user sees that Gmail contributed nothing.
create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  -- queued = accepted and not yet started; the API returns before the work runs.
  status text not null check (status in ('queued', 'running', 'completed', 'failed')),
  triggered_by text not null default 'analyze' check (
    triggered_by in ('analyze', 'sync', 'schedule')
  ),
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
    source in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar',
               'jira', 'notion', 'asana', 'trello')
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
  -- null when a person wrote the action at the dashboard instead of the agent
  -- proposing it as part of a plan.
  run_id uuid references agent_runs(id) on delete cascade,
  -- 'agent' = proposed then approved. 'user' = written by a person, which is its
  -- own approval. Either way it passes the same guard in executor.execute.
  origin text not null default 'agent' check (origin in ('agent', 'user')),
  integration text not null check (
    integration in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar',
                    'jira', 'notion', 'asana', 'trello')
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

-- What the agent concluded while nobody was watching. Written when a scheduled run
-- changes a project's health or fails; `owner_id` is denormalized from the project so
-- the list is one indexed query rather than a join per project.
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

create index if not exists agent_runs_project_idx on agent_runs (project_id, started_at desc);
create index if not exists notifications_owner_idx on notifications (owner_id, created_at desc);
create index if not exists evidence_run_idx on evidence (run_id);
create index if not exists findings_run_idx on findings (run_id);
create index if not exists actions_run_idx on actions (run_id, status);
create index if not exists actions_project_idx on actions (project_id, created_at);
