import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Alert } from '../components/ui/Alert'
import { Card, Panel, SectionHeading } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Icon } from '../components/ui/Icon'
import { Skeleton, SkeletonCards } from '../components/ui/Spinner'
import { ActionCard } from '../features/intelligence/ActionCard'
import { AgentActivityLog } from '../features/intelligence/AgentActivityLog'
import { AskPanel } from '../features/intelligence/AskPanel'
import { FindingCard } from '../features/intelligence/FindingCard'
import { RecoveryPlan } from '../features/intelligence/RecoveryPlan'
import { RunHistory } from '../features/intelligence/RunHistory'
import type { Action, Finding } from '../features/intelligence/types'
import { ProjectHeader } from '../features/projects/ProjectHeader'
import { ProjectState } from '../features/projects/ProjectState'
import type { AgentRun, Project } from '../features/projects/types'
import { api, errorMessage } from '../lib/api'
import { useAppData } from '../lib/appData'
import { plural } from '../lib/format'

export function ProjectPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  // The project list lives in AppLayout; deleting here must refresh the sidebar too.
  const { reload: reloadSidebar } = useAppData()
  const [project, setProject] = useState<Project | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [actions, setActions] = useState<Action[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Approve is a synchronous request, so these ids are what shows Executing while the
  // real apps are actually being written to.
  const [executing, setExecuting] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>([])

  const load = useCallback(async () => {
    const [loadedProject, loadedFindings, loadedActions, loadedRuns] = await Promise.all([
      api.getProject(projectId),
      api.getFindings(projectId),
      api.getActions(projectId),
      api.getRuns(projectId),
    ])
    setProject(loadedProject)
    setFindings(loadedFindings)
    setActions(loadedActions)
    setRuns(loadedRuns)
    setSelected(loadedActions.filter((action) => action.status === 'pending').map((a) => a.id))
  }, [projectId])

  useEffect(() => {
    load()
      .catch((caught) => setError(errorMessage(caught)))
      .finally(() => setLoading(false))
  }, [load])

  async function run(task: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await task()
      await load()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
      setExecuting([])
    }
  }

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((other) => other !== id) : [...current, id],
    )
  }

  function approve() {
    setExecuting(selected)
    void run(() => api.approveActions(projectId, selected))
  }

  async function deleteProject() {
    setDeleting(true)
    setError(null)
    try {
      await api.deleteProject(projectId)
      await reloadSidebar()
      navigate('/app')
    } catch (caught) {
      setError(errorMessage(caught))
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-16 w-full max-w-md" />
        <Skeleton className="h-44 w-full border border-line" />
        <SkeletonCards count={2} height="h-32" />
      </div>
    )
  }

  if (!project) {
    return <Alert title="Project unavailable">{error ?? 'No project was returned.'}</Alert>
  }

  const latestRun = runs[0] ?? null
  const pending = actions.filter((action) => action.status === 'pending')
  const executed = actions.filter((action) => action.status !== 'pending')
  const analyzed = runs.some((item) => item.status === 'completed')

  return (
    <div className="space-y-6">
      <ProjectHeader
        project={project}
        analyzed={analyzed}
        busy={busy}
        onSync={() => run(() => api.syncProject(projectId))}
        deleting={deleting}
        onDelete={() => void deleteProject()}
      />

      {error && <Alert title="The last request failed">{error}</Alert>}

      <ProjectState
        summary={project.summary}
        evidenceCount={latestRun?.evidence_count ?? null}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <AskPanel projects={[project]} />

          <div className="space-y-4">
            <SectionHeading
              title="Findings"
              caption="Every one cites the evidence it was drawn from"
              action={
                findings.length > 0 ? (
                  <span className="text-xs text-faint">
                    {plural(findings.length, 'finding')}
                  </span>
                ) : undefined
              }
            />

            {findings.length === 0 ? (
              <Card>
                <EmptyState
                  icon={<Icon.Search className="h-5 w-5" />}
                  title={analyzed ? 'Nothing was found' : 'Not investigated yet'}
                >
                  {analyzed
                    ? 'The last run collected evidence and concluded there was nothing worth raising. The agent is allowed to find nothing.'
                    : 'Run the analysis to collect evidence from every connected app and cross-reference it.'}
                </EmptyState>
              </Card>
            ) : (
              <div className="space-y-3">
                {findings.map((finding) => (
                  <FindingCard key={finding.id} finding={finding} />
                ))}
              </div>
            )}

            {pending.length > 0 && (
              <div className="pt-2">
                <RecoveryPlan
                  pending={pending}
                  selected={selected}
                  executing={executing}
                  busy={busy}
                  onToggle={toggle}
                  onApprove={approve}
                />
              </div>
            )}

            {executed.length > 0 && (
              <div className="space-y-3 pt-2">
                <SectionHeading
                  title="Execution results"
                  caption="What each approved step did in the connected app"
                />
                {executed.map((action) => (
                  <ActionCard key={action.id} action={action} status={action.status} />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <Panel
            title="Agent activity"
            caption={latestRun ? 'From the latest run' : undefined}
            bodyClassName={latestRun?.activity.length ? 'p-5' : 'p-0'}
          >
            {latestRun?.activity.length ? (
              <AgentActivityLog activity={latestRun.activity} />
            ) : (
              <EmptyState icon={<Icon.Activity className="h-5 w-5" />} title="No activity yet">
                Each node of the workflow reports here as it finishes — including the apps it
                had to skip.
              </EmptyState>
            )}
          </Panel>

          {runs.length > 0 && (
            <Panel title="Run history" caption={plural(runs.length, 'run')}>
              <RunHistory runs={runs} />
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
