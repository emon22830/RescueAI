import type { Source } from '../intelligence/types'

export type Health = 'on_track' | 'watch' | 'at_risk'

export interface ProjectSummary {
  health: Health
  /** The agent's own two or three sentences about where the project stands. */
  summary: string
  /** Percent complete, or null when the evidence did not measure it. */
  progress: number | null
  blockers: number
  risks: number
  findings: number
}

export interface Project {
  id: string
  name: string
  goal: string
  created_at: string
  /** Always present — the latest completed run's state, or zeroes before the first run. */
  summary: ProjectSummary
  /** The apps this project can reach right now. Comes with the project so a card can
   *  show its connectors without one request per project. */
  connected: Source[]
}

/** One line of the agent's log: which node ran and what it came back with. */
export interface AgentActivity {
  agent: string
  status: 'ok' | 'failed'
  detail: string
  evidence_count: number
  at: string
}

export interface AgentRun {
  id: string
  status: 'running' | 'completed' | 'failed'
  triggered_by: 'analyze' | 'sync'
  started_at: string
  completed_at: string | null
  evidence_count: number | null
  finding_count: number | null
  health: Health | null
  summary: string | null
  progress: number | null
  activity: AgentActivity[]
  error: string | null
}
