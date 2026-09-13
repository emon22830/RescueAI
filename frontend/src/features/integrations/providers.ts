import type { Source } from '../intelligence/types'

export interface Provider {
  id: Source
  label: string
  investigates: string
}

export const PROVIDERS: Provider[] = [
  { id: 'slack', label: 'Slack', investigates: 'What the team is saying' },
  { id: 'linear', label: 'Linear', investigates: 'Task status and due dates' },
  { id: 'github', label: 'GitHub', investigates: 'Commits, PRs and issues' },
  { id: 'gmail', label: 'Gmail', investigates: 'Stakeholder communication' },
  { id: 'drive', label: 'Google Drive', investigates: 'Requirements and specs' },
  { id: 'calendar', label: 'Google Calendar', investigates: 'Meetings and deadlines' },
]
