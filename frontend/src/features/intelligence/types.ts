/** Every app the agent can investigate. Mirrors `Source` in app/agents/state.py. */
export type Source =
  // what people said
  | 'slack'
  | 'gmail'
  // what was built
  | 'github'
  // what was planned and tracked
  | 'linear'
  | 'jira'
  | 'asana'
  | 'trello'
  // what was agreed
  | 'drive'
  | 'notion'
  | 'calendar'
export type Severity = 'low' | 'medium' | 'high' | 'critical'

export interface Evidence {
  source: Source
  type: string
  title: string
  content: string
  url: string | null
  timestamp: string | null
  /** App-specific extras the integration kept — issue status, assignee, board, labels.
   *  Nothing renders it: each integration already folds the readable parts into
   *  `content`, so showing it too would print the same facts twice. It is typed because
   *  the API sends it, and because a future filter ("only what is overdue") wants it. */
  metadata?: Record<string, unknown>
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

/** What a step does, in the words a project manager uses. */
export type ActionVerb = 'add' | 'update' | 'delegate' | 'close' | 'message'

/** One thing a project can be asked to do, and what its two fields mean.
 *  Served by `GET /projects/{id}/actions/types` and limited to the apps the project
 *  has connected — the composer is built from this, never from a hardcoded list. */
export interface ActionType {
  integration: Source
  type: string
  verb: ActionVerb
  label: string
  target_label: string
  value_label: string
}

export interface Action {
  id: string
  integration: Source
  /** One of the types from `ActionType` — see `GET /actions/types`. */
  type: string
  /** `agent` = proposed in a recovery plan, then approved.
   *  `user` = written by a person at the dashboard, which is its own approval. */
  origin: 'agent' | 'user'
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
