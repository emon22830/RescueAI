import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { Alert } from '../components/ui/Alert'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Spinner'
import { ConnectionCard } from '../features/integrations/ConnectionCard'
import type { IntegrationStatus } from '../features/integrations/types'
import type { Project } from '../features/projects/types'
import { api, errorMessage } from '../lib/api'

export function ConnectionsPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Google sends the browser back here with the outcome of the consent screen.
  const [params, setParams] = useSearchParams()
  const googleResult = params.get('google')

  useEffect(() => {
    Promise.all([api.getProject(projectId), api.listIntegrations(projectId)])
      .then(([loadedProject, loadedIntegrations]) => {
        setProject(loadedProject)
        setIntegrations(loadedIntegrations)
      })
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [projectId])

  // Read once, then drop it from the URL so a refresh does not replay the outcome.
  useEffect(() => {
    if (!googleResult) return
    const next = new URLSearchParams(params)
    next.delete('google')
    setParams(next, { replace: true })
    // params/setParams are intentionally omitted: this must run only on the value itself.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [googleResult])

  function replace(updated: IntegrationStatus) {
    setIntegrations((current) =>
      current.map((app) => (app.id === updated.id ? updated : app)),
    )
  }

  const connected = integrations.filter((app) => app.connected).length

  return (
    <div className="space-y-6">
      {googleResult && googleResult !== 'connected' && (
        <Alert title="Google was not connected">
          {googleResult === 'access_denied'
            ? 'You declined the consent screen, so nothing was saved. Try again when ready.'
            : `Google returned "${googleResult}". Nothing was saved — try connecting again.`}
        </Alert>
      )}
      <div>
        <Link
          to={`/app/projects/${projectId}`}
          className="text-xs font-semibold text-faint transition-colors duration-150 hover:text-ink"
        >
          ← {project?.name ?? 'Back to project'}
        </Link>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Connections</h1>
        <p className="mt-1 text-sm text-muted">
          The apps this project can investigate. An app with no credential is skipped — it
          contributes no evidence, and nothing is invented to fill the gap.
        </p>
      </div>

      {!loading && !error && (
        <Card className="flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <Icon.Plug className="h-4 w-4 text-muted" />
            <span className="text-sm">
              <span className="font-bold tabular-nums">{connected}</span>
              <span className="text-muted"> of {integrations.length} connected</span>
            </span>
          </div>
          <p className="flex items-center gap-2 text-xs text-faint">
            <Icon.Shield className="h-4 w-4 shrink-0" />
            Tokens are verified against the real app, then stored encrypted for this project
            alone. This page never displays a credential back.
          </p>
        </Card>
      )}

      {error && <Alert title="Could not read connection status">{error}</Alert>}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1, 2, 3, 4, 5].map((card) => (
            <Skeleton key={card} className="h-72 w-full border border-line" />
          ))}
        </div>
      ) : (
        <div className="grid items-start gap-4 md:grid-cols-2">
          {integrations.map((status) => (
            <ConnectionCard
              key={status.id}
              projectId={projectId}
              status={status}
              onChanged={replace}
            />
          ))}
        </div>
      )}
    </div>
  )
}
