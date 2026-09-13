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

/** Why the answer reads the way it does. `chat` is a hello or a question about the
 *  agent itself — not a hole in the evidence, so it is never flagged as one. */
export type AnswerKind = 'answer' | 'gap' | 'chat'

/** One answer from `POST /projects/{id}/ask`.
 *  `answered` is false when the collected evidence could not answer the question — the
 *  UI says so rather than presenting a guess as an answer. */
export interface Answer {
  question: string
  /** Markdown: bold, inline code, bullets and one level of heading. */
  answer: string
  answered: boolean
  kind: AnswerKind
  /** Up to three questions the same evidence could answer next. */
  follow_ups: string[]
  evidence: Evidence[]
}
