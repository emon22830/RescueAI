import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Stat } from '../components/ui/Card'
import { HealthBadge } from '../components/ui/Badge'
import { ActionCard } from '../features/intelligence/ActionCard'
import { FindingCard } from '../features/intelligence/FindingCard'
import type { Action, Finding } from '../features/intelligence/types'
import type { Project } from '../features/projects/types'
import { api } from '../lib/api'

export function ProjectPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [actions, setActions] = useState<Action[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // The ids currently being executed. The approve request is synchronous, so this is
  // what lets the plan show EXECUTING while the apps are actually being written to.
  const [executing, setExecuting] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>([])

  const load = useCallback(async () => {
    const [loadedProject, loadedFindings, loadedActions] = await Promise.all([
      api.getProject(projectId),
      api.getFindings(projectId),
      api.getActions(projectId),
    ])
    setProject(loadedProject)
    setFindings(loadedFindings)
    setActions(loadedActions)
    setSelected(loadedActions.filter((action) => action.status === 'pending').map((a) => a.id))
  }, [projectId])

  useEffect(() => {
    load().catch((caught: Error) => setError(caught.message))
  }, [load])

  async function run(task: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await task()
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  if (!project) {
    return <p className="text-sm text-slate-500">{error ?? 'Loading…'}</p>
  }

  const pending = actions.filter((action) => action.status === 'pending')
  const done = actions.filter((action) => action.status !== 'pending')

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((other) => other !== id) : [...current, id],
    )
  }

  async function approve() {
    setExecuting(selected)
    await run(() => api.approveActions(projectId, selected))
    setExecuting([])
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <p className="text-sm text-slate-600">{project.goal}</p>
        </div>
        <div className="flex items-center gap-3">
          {project.summary && <HealthBadge health={project.summary.health} />}
          <button
            onClick={() => run(() => api.syncProject(projectId))}
            disabled={busy}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? 'Analyzing…' : 'Sync project'}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}

      {project.summary && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Blockers" value={project.summary.blockers} />
          <Stat label="Risks" value={project.summary.risks} />
          <Stat label="Findings" value={project.summary.findings} />
        </div>
      )}

      <section className="space-y-3">
        <h2 className="font-medium">Findings</h2>
        {findings.length === 0 ? (
          <p className="text-sm text-slate-500">
            Nothing yet. Run a sync to investigate the connected apps.
          </p>
        ) : (
          findings.map((finding) => <FindingCard key={finding.id} finding={finding} />)
        )}
      </section>

      {pending.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Recovery plan</h2>
            <p className="text-sm text-slate-500">
              Nothing is sent to Linear, Calendar or Gmail until you approve it.
            </p>
          </div>

          {pending.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              status={executing.includes(action.id) ? 'executing' : 'pending'}
              selected={selected.includes(action.id)}
              onToggle={() => toggle(action.id)}
            />
          ))}

          <button
            onClick={approve}
            disabled={busy || selected.length === 0}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? 'Executing…' : `Approve & execute ${selected.length} action${selected.length === 1 ? '' : 's'}`}
          </button>
        </section>
      )}

      {done.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium">Actions taken</h2>
          {done.map((action) => (
            <ActionCard key={action.id} action={action} status={action.status} />
          ))}
        </section>
      )}
    </div>
  )
}
