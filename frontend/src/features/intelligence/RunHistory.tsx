import { Badge } from '../../components/ui/Badge'
import { duration, timeAgo } from '../../lib/format'
import type { AgentRun } from '../projects/types'

const STATUS_TONE = {
  completed: 'success',
  running: 'warn',
  failed: 'danger',
} as const

export function RunHistory({ runs }: { runs: AgentRun[] }) {
  return (
    <ul className="divide-y divide-line">
      {runs.map((run) => (
        <li key={run.id} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
          <Badge tone={STATUS_TONE[run.status]}>
            {run.triggered_by === 'sync' ? 'Sync' : 'Analysis'}
          </Badge>
          <span className="text-xs text-muted">
            {run.evidence_count ?? 0} evidence · {run.finding_count ?? 0} findings
          </span>
          <span className="ml-auto shrink-0 text-xs text-faint">
            {timeAgo(run.started_at)} · {duration(run.started_at, run.completed_at)}
          </span>
        </li>
      ))}
    </ul>
  )
}
