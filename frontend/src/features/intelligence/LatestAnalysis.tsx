import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Panel } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Icon } from '../../components/ui/Icon'
import { duration, timeAgo } from '../../lib/format'
import type { AgentRun, Project } from '../projects/types'
import { AgentActivityLog } from './AgentActivityLog'

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
      caption={`${run.triggered_by === 'sync' ? 'Sync' : 'Analysis'} · ${timeAgo(run.started_at)}`}
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
        <Badge tone={run.status === 'failed' ? 'danger' : 'success'}>
          {run.status === 'failed' ? 'Failed' : 'Completed'}
        </Badge>
        <Badge>{run.evidence_count ?? 0} evidence</Badge>
        <Badge>{run.finding_count ?? 0} findings</Badge>
        <Badge>{duration(run.started_at, run.completed_at)}</Badge>
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
