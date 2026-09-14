import type { Source } from '../intelligence/types'

/**
 * How each app is described to a user. The *truth* about a connection — whether it is
 * configured, and what is still needed — comes from `GET /projects/{id}/integrations`; only
 * lives here.
 */
export interface ProviderCopy {
  investigates: string
  collects: string
  /** The workflow node that reads this app. */
  agent: string
}

export const PROVIDERS: Record<Source, ProviderCopy> = {
  slack: {
    investigates: 'What the team is saying',
    collects: 'Recent messages in channels about the project',
    agent: 'Communication',
  },
  gmail: {
    investigates: 'Stakeholder communication',
    collects: 'Threads where requirements and dates get changed',
    agent: 'Communication',
  },
  github: {
    investigates: 'What has actually been built',
    collects: 'Commits, pull requests and issues from the last 30 days',
    agent: 'Engineering',
  },
  linear: {
    investigates: 'Task status and due dates',
    collects: 'Issues, their state, assignee and what is overdue',
    agent: 'Engineering',
  },
  drive: {
    investigates: 'Requirements and specs',
    collects: 'Documents about the project, and when they last changed',
    agent: 'Requirements',
  },
  calendar: {
    investigates: 'Meetings and deadlines',
    collects: 'Upcoming reviews, launches and milestones',
    agent: 'Requirements',
  },
  jira: {
    investigates: 'Task status and due dates',
    collects: 'Issues, their status, assignee and what is overdue',
    agent: 'Delivery',
  },
  asana: {
    investigates: 'Task status and due dates',
    collects: 'Tasks in the matching project, and what is past due',
    agent: 'Delivery',
  },
  trello: {
    investigates: 'What the board says',
    collects: 'Cards that mention the project, and where they sit',
    agent: 'Delivery',
  },
  notion: {
    investigates: 'Requirements and specs',
    collects: 'Pages about the project, and when they last changed',
    agent: 'Requirements',
  },
}

/** The order every surface lists the apps in, grouped the way the workflow reads them:
 *  what people said, what was built, what was planned, then what was agreed. */
export const SOURCE_ORDER: Source[] = [
  'slack',
  'gmail',
  'github',
  'linear',
  'jira',
  'asana',
  'trello',
  'drive',
  'notion',
  'calendar',
]

/** What each token app calls the credential it wants pasted. */
export const CREDENTIAL_LABEL: Partial<Record<Source, string>> = {
  slack: 'Bot token (xoxb-…)',
  linear: 'Personal API key',
  github: 'Fine-grained access token',
  jira: 'API token',
  asana: 'Personal access token',
  trello: 'User token',
  notion: 'Internal integration token',
}

export interface ExtraField {
  /** Matches the field name on ConnectIntegrationRequest in app/api/integrations.py. */
  name: 'repo' | 'channel_ids' | 'site' | 'email' | 'project_key' | 'key' | 'workspace'
  label: string
  hint?: string
  placeholder?: string
  required?: boolean
}

/**
 * Everything an app needs besides the credential itself, declared rather than branched
 * on — ten apps of `if (provider === …)` is how a connect form stops being readable.
 *
 * Nothing secret belongs here: these are stored as metadata and read back to the owner.
 * Trello's `key` is the exception that proves the rule — it identifies the application,
 * not the user, and the token beside it is the half that gets encrypted.
 */
export const EXTRA_FIELDS: Partial<Record<Source, ExtraField[]>> = {
  github: [
    { name: 'repo', label: 'Repository', hint: 'owner/name, or a URL', placeholder: 'owner/name', required: true },
  ],
  slack: [
    {
      name: 'channel_ids',
      label: 'Channel IDs',
      hint: 'optional',
      placeholder: 'C01ABC,C02DEF — leave blank to read every invited channel',
    },
  ],
  jira: [
    { name: 'site', label: 'Site', hint: 'the host, not a page URL', placeholder: 'acme.atlassian.net', required: true },
    {
      name: 'email',
      label: 'Account email',
      hint: 'the account this API token was issued for',
      placeholder: 'you@acme.com',
      required: true,
    },
    {
      name: 'project_key',
      label: 'Project key',
      hint: 'optional — narrows collection, and is where new issues are created',
      placeholder: 'PAY',
    },
  ],
  trello: [
    {
      name: 'key',
      label: 'API key',
      hint: 'the key the token was generated against',
      placeholder: 'From the Power-Ups admin page',
      required: true,
    },
  ],
  asana: [
    {
      name: 'workspace',
      label: 'Workspace ID',
      hint: 'optional — defaults to the first workspace this token can see',
    },
  ],
}
