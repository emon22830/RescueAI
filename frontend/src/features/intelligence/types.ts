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

export interface Action {
  id: string
  integration: Source
  action: string
  description: string
  params: Record<string, string>
  status: 'pending' | 'executed' | 'failed'
  result: string | null
}
