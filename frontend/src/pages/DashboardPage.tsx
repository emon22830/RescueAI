import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, SectionHeading } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Icon } from '../components/ui/Icon'
import { SkeletonCards } from '../components/ui/Spinner'
import { StatTile } from '../components/ui/StatTile'
import { ConnectionsSummary } from '../features/integrations/ConnectionsSummary'
import type { IntegrationStatus } from '../features/integrations/types'
import { AskPanel } from '../features/intelligence/AskPanel'
import { LatestAnalysis } from '../features/intelligence/LatestAnalysis'
import { CreateProjectForm } from '../features/projects/CreateProjectForm'
import { ProjectCard } from '../features/projects/ProjectCard'
import type { AgentRun, Project } from '../features/projects/types'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'

/** Portfolio totals, summed from the stored state of each project's latest run. */
function totals(projects: Project[]) {
  return projects.reduce(
    (sum, project) => ({
      blockers: sum.blockers + project.summary.blockers,
      risks: sum.risks + project.summary.risks,
      findings: sum.findings + project.summary.findings,
      atRisk: sum.atRisk + (project.summary.health === 'at_risk' ? 1 : 0),
    }),
    { blockers: 0, risks: 0, findings: 0, atRisk: 0 },
  )
}

export function DashboardPage() {
  // The project list is owned by AppLayout so the sidebar and this page always agree.
  const { projects, loading, error, reload } = useAppData()
  const [latestRun, setLatestRun] = useState<AgentRun | null>(null)

  // Connections belong to a project, so this panel follows the same featured project
  // the activity panel does. It fails on its own — a connections error must not blank
  // the project list, or the other way round.
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [integrationsLoading, setIntegrationsLoading] = useState(true)
  const [integrationsError, setIntegrationsError] = useState<string | null>(null)

  // The sidebar's "New project" links here with ?new=1, so the form opens on arrival.
  const [params, setParams] = useSearchParams()
  const [creating, setCreating] = useState(params.get('new') === '1')

  const featured = projects[0] ?? null

  useEffect(() => {
    if (!featured) {
      setLatestRun(null)
      setIntegrations([])
      setIntegrationsLoading(false)
      return
    }
    setIntegrationsLoading(true)
    setIntegrationsError(null)
    void Promise.all([api.getRuns(featured.id), api.listIntegrations(featured.id)])
      .then(([runs, apps]) => {
        setLatestRun(runs[0] ?? null)
        setIntegrations(apps)
      })
      .catch((caught) => setIntegrationsError(errorMessage(caught)))
      .finally(() => setIntegrationsLoading(false))
  }, [featured])

  function openCreate(open: boolean) {
    setCreating(open)
    // Keep the URL honest, so a refresh does not reopen a form you just closed.
    if (!open && params.get('new')) setParams({}, { replace: true })
  }

  const summed = totals(projects)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted">
            Project state rebuilt from evidence in the apps your team already uses.
          </p>
        </div>
        <Button
          variant={creating ? 'secondary' : 'primary'}
          onClick={() => openCreate(!creating)}
          icon={creating ? undefined : <Icon.Plus className="h-4 w-4" />}
        >
          {creating ? 'Cancel' : 'New project'}
        </Button>
      </div>

      {creating && (
        <CreateProjectForm
          onCreated={() => {
            // Re-read the list so the sidebar gains the project too.
            void reload()
            openCreate(false)
          }}
        />
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="Projects"
          value={loading ? '—' : projects.length}
          caption={summed.atRisk > 0 ? `${summed.atRisk} at risk` : 'None at risk'}
        />
        <StatTile
          label="Blockers"
          value={loading ? '—' : summed.blockers}
          tone={summed.blockers > 0 ? 'danger' : 'neutral'}
          caption="Stopping work right now"
        />
        <StatTile
          label="Risks"
          value={loading ? '—' : summed.risks}
          tone={summed.risks > 0 ? 'warn' : 'neutral'}
          caption="Likely to stop it soon"
        />
        <StatTile
          label="Findings"
          value={loading ? '—' : summed.findings}
          caption="Each one cites its evidence"
        />
      </div>

      {error && (
        <Alert title="Could not load projects">{error}</Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <AskPanel projects={projects} />

          <div className="space-y-4">
            <SectionHeading
              title="Projects"
              caption="Health and progress from each project's latest completed run"
            />

            {loading && <SkeletonCards count={2} height="h-52" />}

            {!loading && error && (
              <Card>
                <EmptyState
                  icon={<Icon.Warning className="h-5 w-5" />}
                  title="Projects are unavailable"
                >
                  Projects live in Supabase, and the backend could not reach it. Fix the
                  variables named above and reload — the rest of this page does not depend on
                  the database.
                </EmptyState>
              </Card>
            )}

            {!loading && !error && projects.length === 0 && (
              <Card>
                <EmptyState
                  icon={<Icon.Search className="h-5 w-5" />}
                  title="No projects tracked yet"
                  action={
                    <Button variant="primary" onClick={() => openCreate(true)}>
                      Create the first project
                    </Button>
                  }
                >
                  Name a project the way your team names it in Slack and Linear. The agent uses
                  that name to find the evidence.
                </EmptyState>
              </Card>
            )}

            {projects.length > 0 && (
              <div className="grid gap-4 sm:grid-cols-2">
                {projects.map((project) => (
                  <ProjectCard key={project.id} project={project} />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <ConnectionsSummary
            projectId={featured?.id ?? null}
            projectName={featured?.name ?? null}
            integrations={integrations}
            loading={integrationsLoading}
            error={integrationsError}
          />
          <LatestAnalysis project={featured} run={latestRun} />
        </div>
      </div>
    </div>
  )
}
