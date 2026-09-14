import { Badge } from '../../components/ui/Badge'
import { duration, timeAgo } from '../../lib/format'
import type { AgentRun } from '../projects/types'

const STATUS_TONE = {
  completed: 'success',
  queued: 'neutral',
  running: 'warn',
  failed: 'danger',
} as const

/** Which button — or which scheduler tick — started this run. */
const TRIGGER_LABEL = {
  analyze: 'Analysis',
  sync: 'Sync',
  schedule: 'Scheduled',
} as const

export function RunHistory({ runs }: { runs: AgentRun[] }) {
  return (
    <ul className="divide-y divide-line">
      {runs.map((run) => {
        const finished = run.status === 'completed' || run.status === 'failed'
        return (
          <li key={run.id} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
            <Badge tone={STATUS_TONE[run.status]}>{TRIGGER_LABEL[run.triggered_by]}</Badge>
            <span className="text-xs text-muted">
              {/* A run that has not finished has no counts yet — saying "0 evidence"
                  would read as "looked and found nothing". */}
              {finished
                ? `${run.evidence_count ?? 0} evidence · ${run.finding_count ?? 0} findings`
                : run.status === 'queued'
                  ? 'Queued'
                  : 'Investigating…'}
            </span>
            <span className="ml-auto shrink-0 text-xs text-faint">
              {timeAgo(run.started_at)}
              {finished && ` · ${duration(run.started_at, run.completed_at)}`}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
