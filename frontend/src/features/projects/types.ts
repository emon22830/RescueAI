export interface ProjectSummary {
  health: 'on_track' | 'watch' | 'at_risk'
  blockers: number
  risks: number
  findings: number
}

export interface Project {
  id: string
  name: string
  goal: string
  created_at: string
  summary?: ProjectSummary
}

export interface AgentRun {
  id: string
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at: string | null
  evidence_count: number | null
  finding_count: number | null
  error: string | null
}
