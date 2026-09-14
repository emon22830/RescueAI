import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Panel } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Icon } from '../../components/ui/Icon'
import { duration, timeAgo } from '../../lib/format'
import type { AgentRun, Project } from '../projects/types'
import { AgentActivityLog } from './AgentActivityLog'

/** The run's real state, said plainly. A run that has not finished must never read as
 *  "Completed" — the dashboard is the one place someone checks instead of looking. */
const STATUS = {
  queued: { label: 'Queued', tone: 'neutral' },
  running: { label: 'Investigating…', tone: 'warn' },
  completed: { label: 'Completed', tone: 'success' },
  failed: { label: 'Failed', tone: 'danger' },
} as const

const TRIGGER_LABEL = { analyze: 'Analysis', sync: 'Sync', schedule: 'Scheduled' } as const

/**
 * The most recent pass of the workflow on one project: what it cost and what each node
 * came back with. Which project it describes is named, never implied.
 */
export function LatestAnalysis({ project, run }: { project: Project | null; run: AgentRun | null }) {
  if (!project || !run) {
    return (
      <Panel title="Latest analysis" bodyClassName="p-0">
        <EmptyState icon={<Icon.Activity className="h-5 w-5" />} title="No run yet">
          Open a project and run the analysis. Every node of the workflow reports here as it
          finishes.
        </EmptyState>
      </Panel>
    )
  }

  return (
    <Panel
      title="Latest analysis"
      caption={`${TRIGGER_LABEL[run.triggered_by]} · ${timeAgo(run.started_at)}`}
      action={
        <Link
          to={`/app/projects/${project.id}`}
          className="shrink-0 truncate text-xs font-medium text-brand transition-colors duration-150 hover:text-brand-hover"
        >
          {project.name}
        </Link>
      }
      bodyClassName="p-5 space-y-4"
    >
      <div className="flex flex-wrap gap-1.5">
        <Badge tone={STATUS[run.status].tone}>{STATUS[run.status].label}</Badge>
        {/* Counts and duration only exist once the run has finished. */}
        {run.completed_at && (
          <>
            <Badge>{run.evidence_count ?? 0} evidence</Badge>
            <Badge>{run.finding_count ?? 0} findings</Badge>
            <Badge>{duration(run.started_at, run.completed_at)}</Badge>
          </>
        )}
      </div>

      {run.error && <p className="text-sm text-danger">{run.error}</p>}

      {run.activity.length > 0 ? (
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
            Agent activity
          </p>
          <AgentActivityLog activity={run.activity} />
        </div>
      ) : (
        <p className="text-sm text-faint">This run recorded no node activity.</p>
      )}
    </Panel>
  )
}
