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
}

/** The order every surface lists the apps in: the two communication apps, the two
 *  engineering apps, then the two requirements apps. */
export const SOURCE_ORDER: Source[] = ['slack', 'gmail', 'github', 'linear', 'drive', 'calendar']
