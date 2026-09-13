import { Link } from 'react-router-dom'

import { Panel } from '../../components/ui/Card'
import { plural } from '../../lib/format'
import { Icon } from '../../components/ui/Icon'
import { Skeleton } from '../../components/ui/Spinner'
import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import type { IntegrationStatus } from './types'

/** The dashboard's compact read of what the agent can currently reach. */
export function ConnectionsSummary({
  projectId,
  projectName,
  integrations,
  loading,
  error,
}: {
  /** Which project these belong to — null before any project exists. */
  projectId: string | null
  projectName: string | null
  integrations: IntegrationStatus[]
  loading: boolean
  error: string | null
}) {
  const connected = integrations.filter((app) => app.connected).length

  return (
    <Panel
      title="Connected applications"
      caption={
        projectName && !loading && !error
          ? `${connected} of ${integrations.length} on ${projectName}`
          : undefined
      }
      action={
        projectId ? (
          <Link
            to={`/app/projects/${projectId}/connections`}
            className="shrink-0 text-xs font-semibold text-brand transition-colors duration-150 hover:text-brand-hover"
          >
            Manage
          </Link>
        ) : undefined
      }
      bodyClassName="p-3"
    >
      {loading && (
        <div className="space-y-1.5 p-1">
          {[0, 1, 2, 3, 4, 5].map((row) => (
            <Skeleton key={row} className="h-9 w-full" />
          ))}
        </div>
      )}

      {error && <p className="p-2 text-sm text-danger">{error}</p>}

      {!loading && !error && integrations.length === 0 && (
        <p className="p-2 text-sm text-faint">
          Create a project to connect the apps it should investigate.
        </p>
      )}

      {!loading && !error && (
        <ul>
          {integrations.map((app) => (
            <li
              key={app.id}
              className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm transition-colors duration-150 hover:bg-raised"
            >
              <SourceIcon source={app.id} className="h-4 w-4 shrink-0 text-muted" />
              <span className="truncate font-medium text-ink">{SOURCE_LABELS[app.id]}</span>
              {app.connected ? (
                <Icon.Check className="ml-auto h-4 w-4 shrink-0 text-success" />
              ) : (
                <span className="ml-auto shrink-0 text-xs text-faint">
                  {app.mode === 'token'
                    ? 'Needs a token'
                    : plural(app.variables.length, 'variable')}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
