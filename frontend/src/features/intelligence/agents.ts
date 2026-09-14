import type { Source } from './types'

/**
 * The nodes of the one workflow, in the order they run. The graph is the product, so
 * the activity log names each node rather than showing an opaque "agent".
 */
export const AGENTS: Record<string, { label: string; reads: Source[]; does: string }> = {
  supervisor: { label: 'Supervisor', reads: [], does: 'Planned the investigation' },
  communication: { label: 'Communication', reads: ['slack', 'gmail'], does: 'What the team is saying' },
  engineering: { label: 'Engineering', reads: ['github'], does: 'What has actually been built' },
  delivery: {
    label: 'Delivery',
    reads: ['linear', 'jira', 'asana', 'trello'],
    does: 'What the plan says, and what is overdue',
  },
  requirements: {
    label: 'Requirements',
    reads: ['drive', 'notion', 'calendar'],
    does: 'What was agreed, and when',
  },
  risk: { label: 'Risk', reads: [], does: 'Cross-referenced everything into findings' },
  recovery: { label: 'Recovery', reads: [], does: 'Turned the findings into a plan' },
}

export function agentLabel(name: string): string {
  return AGENTS[name]?.label ?? name.charAt(0).toUpperCase() + name.slice(1)
}
