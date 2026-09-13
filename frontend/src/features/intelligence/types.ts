export type Source = 'slack' | 'gmail' | 'drive' | 'linear' | 'github' | 'calendar'
export type Severity = 'low' | 'medium' | 'high' | 'critical'

export interface Evidence {
  source: Source
  type: string
  title: string
  content: string
  url: string | null
  timestamp: string | null
}

export interface Finding {
  id: string
  title: string
  severity: Severity
  confidence: number
  description: string
  evidence: Evidence[]
  created_at: string
}

/** Proposed by the agent, approved by a human, run, then done or not. */
export type ActionStatus = 'pending' | 'approved' | 'executing' | 'completed' | 'failed'

export interface Action {
  id: string
  integration: Source
  /** "update_issue" | "assign_task" | "update_due_date" | "create_event" | "send_email" */
  type: string
  description: string
  /** What it acts on: the issue, the attendees, the recipient. */
  target: string
  /** The finding this action is meant to fix. */
  reason: string
  params: Record<string, string>
  status: ActionStatus
  /** What the app said back, or why it failed. */
  result: string | null
  approved_at: string | null
  executed_at: string | null
}
