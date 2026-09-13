import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '../../components/ui/Alert'
import { HealthBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import type { Project } from './types'

/** Title block of the project page: what it is, how it is, and the one action here. */
export function ProjectHeader({
  project,
  analyzed,
  busy,
  onSync,
  deleting,
  onDelete,
}: {
  project: Project
  /** False until a run has produced a state — the button says Analyze, not Sync. */
  analyzed: boolean
  busy: boolean
  onSync: () => void
  deleting: boolean
  onDelete: () => void
}) {
  const [confirming, setConfirming] = useState(false)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            to="/app"
            className="text-xs font-medium text-faint transition-colors duration-150 hover:text-ink"
          >
            ← All projects
          </Link>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight">{project.name}</h1>
            <HealthBadge health={project.summary.health} />
          </div>
          <p className="mt-1 text-sm text-muted">{project.goal}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/app/projects/${project.id}/connections`}>
            <Button variant="secondary" icon={<Icon.Plug className="h-4 w-4" />}>
              Connections
            </Button>
          </Link>
          <Button
            variant="primary"
            loading={busy}
            onClick={onSync}
            icon={<Icon.Refresh className="h-4 w-4" />}
          >
            {busy ? 'Investigating…' : analyzed ? 'Re-sync project' : 'Run analysis'}
          </Button>
          <Button
            variant="ghost"
            onClick={() => setConfirming(true)}
            icon={<Icon.Trash className="h-4 w-4" />}
            className="text-faint hover:text-danger"
          >
            Delete
          </Button>
        </div>
      </div>

      {confirming && (
        <Alert
          tone="danger"
          title="Delete this project?"
          action={
            <div className="flex shrink-0 items-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" loading={deleting} onClick={onDelete}>
                {deleting ? 'Deleting…' : 'Delete project'}
              </Button>
            </div>
          }
        >
          Everything collected about <span className="font-semibold">{project.name}</span> —
          evidence, findings, runs and the recovery plan — is deleted with it. This cannot be
          undone.
        </Alert>
      )}
    </div>
  )
}
