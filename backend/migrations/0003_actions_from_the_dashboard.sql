-- Phase 3: an action does not have to come from a plan.
--
-- Until now every action was a step of a recovery plan, so it always belonged to the
-- run that proposed it. A user taking an action straight from the dashboard has no run
-- behind them — and may not have analysed the project at all yet — so `run_id` becomes
-- optional, and `origin` records who authored the action.
--
-- Safe to run on an existing database. Run it in the Supabase SQL editor.

alter table actions alter column run_id drop not null;

-- 'agent' = proposed by the recovery node and approved by a human.
-- 'user'  = written by a person at the dashboard, which is its own approval.
alter table actions add column if not exists origin text not null default 'agent'
  check (origin in ('agent', 'user'));

-- Manual actions are read by project, not by run.
create index if not exists actions_project_idx on actions (project_id, created_at);
