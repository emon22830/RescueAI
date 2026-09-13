import { Link } from 'react-router-dom'

import { HealthBadge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { ProgressBar } from '../../components/ui/ProgressBar'
import { ConnectorStrip } from '../integrations/ConnectorStrip'
import { timeAgo } from '../../lib/format'
import type { Project } from './types'

function Count({ label, value, alarming }: { label: string; value: number; alarming?: boolean }) {
  return (
    <div>
      <div
        className={`text-lg font-semibold tabular-nums ${
          alarming && value > 0 ? 'text-danger' : 'text-ink'
        }`}
      >
        {value}
      </div>
      <div className="text-xs text-faint">{label}</div>
    </div>
  )
}

export function ProjectCard({ project }: { project: Project }) {
  const summary = project.summary

  return (
    <Link to={`/app/projects/${project.id}`} className="block">
      <Card interactive className="h-full p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate font-semibold tracking-tight">{project.name}</h3>
            <p className="mt-0.5 truncate text-sm text-muted">{project.goal}</p>
          </div>
          <HealthBadge health={summary.health} />
        </div>

        {summary.summary ? (
          <p className="mt-4 line-clamp-2 text-sm text-muted">{summary.summary}</p>
        ) : (
          <p className="mt-4 text-sm text-faint">
            Not analyzed yet — open the project to run the agent.
          </p>
        )}

        <div className="mt-5">
          <ProgressBar value={summary.progress} />
        </div>

        <div className="mt-5 border-t border-line pt-4">
          <ConnectorStrip connected={project.connected} />
        </div>

        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-t border-line pt-4">
          <div className="flex gap-5">
            <Count label="Blockers" value={summary.blockers} alarming />
            <Count label="Risks" value={summary.risks} alarming />
            <Count label="Findings" value={summary.findings} />
          </div>
          <span className="shrink-0 whitespace-nowrap text-xs text-faint">
            Created {timeAgo(project.created_at)}
          </span>
        </div>
      </Card>
    </Link>
  )
}
