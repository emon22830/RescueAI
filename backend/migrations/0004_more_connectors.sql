-- Jira, Notion, Asana and Trello.
--
-- Three check constraints in this schema name every app by hand: which sources evidence
-- may come from, which apps an action may target, and which credentials may be stored.
-- A new connector is invisible to all three until they are widened, and the failure is
-- a constraint violation deep inside a run rather than anything the user can read.
--
-- Safe to run on an existing database. Run it in the Supabase SQL editor.

-- 1 — evidence may now come from ten apps.
alter table evidence drop constraint if exists evidence_source_check;
alter table evidence add constraint evidence_source_check check (
  source in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar',
             'jira', 'notion', 'asana', 'trello')
);

-- 2 — an action may target any app that can be written to.
alter table actions drop constraint if exists actions_integration_check;
alter table actions add constraint actions_integration_check check (
  integration in ('slack', 'gmail', 'drive', 'linear', 'github', 'calendar',
                  'jira', 'notion', 'asana', 'trello')
);

-- 3 — seven apps now store a per-project credential. 'google' remains one row covering
-- Gmail, Drive and Calendar: three APIs behind a single consent.
alter table integrations drop constraint if exists integrations_provider_check;
alter table integrations add constraint integrations_provider_check check (
  provider in ('slack', 'linear', 'github', 'google', 'jira', 'notion', 'asana', 'trello')
);
