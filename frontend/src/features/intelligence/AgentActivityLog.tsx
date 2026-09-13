import { SourceIcon } from '../../components/ui/SourceIcon'
import { timeAgo } from '../../lib/format'
import type { AgentActivity } from '../projects/types'
import { AGENTS, agentLabel } from './agents'

/** One row per node that ran. A failure reads as plainly as a success. */
function Row({ activity }: { activity: AgentActivity }) {
  const meta = AGENTS[activity.agent]
  const failed = activity.status === 'failed'

  return (
    <li className="flex gap-3 py-3 first:pt-0 last:pb-0">
      <span
        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${failed ? 'bg-danger' : 'bg-success'}`}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-medium text-ink">{agentLabel(activity.agent)}</span>
          <span className="shrink-0 text-xs text-faint">{timeAgo(activity.at)}</span>
        </div>
        <p className={`mt-0.5 text-sm ${failed ? 'text-danger' : 'text-muted'}`}>
          {activity.detail}
        </p>
        {meta && meta.reads.length > 0 && (
          <div className="mt-1.5 flex items-center gap-2 text-xs text-faint">
            <span className="flex items-center gap-1">
              {meta.reads.map((source) => (
                <SourceIcon key={source} source={source} className="h-3.5 w-3.5" />
              ))}
            </span>
            <span>
              {activity.evidence_count} {activity.evidence_count === 1 ? 'item' : 'items'} collected
            </span>
          </div>
        )}
      </div>
    </li>
  )
}

export function AgentActivityLog({ activity }: { activity: AgentActivity[] }) {
  return (
    <ul className="divide-y divide-line">
      {activity.map((entry, index) => (
        <Row key={`${entry.agent}-${index}`} activity={entry} />
      ))}
    </ul>
  )
}
