import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Card, Stat } from '../components/ui/Card'
import { HealthBadge } from '../components/ui/Badge'
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

  const load = useCallback(async () => {
    const [loadedProject, loadedFindings, loadedActions] = await Promise.all([
      api.getProject(projectId),
      api.getFindings(projectId),
      api.getActions(projectId),
    ])
    setProject(loadedProject)
    setFindings(loadedFindings)
    setActions(loadedActions)
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
  const executed = actions.filter((action) => action.status !== 'pending')

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
          <h2 className="font-medium">Recovery plan</h2>
          {pending.map((action) => (
            <Card key={action.id}>
              <div className="text-xs font-medium uppercase text-slate-500">
                {action.integration} · {action.action}
              </div>
              <p className="text-sm">{action.description}</p>
            </Card>
          ))}
          <button
            onClick={() =>
              run(() => api.approveActions(projectId, pending.map((action) => action.id)))
            }
            disabled={busy}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Approve &amp; execute
          </button>
        </section>
      )}

      {executed.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium">Executed actions</h2>
          {executed.map((action) => (
            <Card key={action.id}>
              <div className="flex items-center justify-between">
                <p className="text-sm">{action.description}</p>
                <span
                  className={
                    action.status === 'executed' ? 'text-sm text-emerald-700' : 'text-sm text-red-700'
                  }
                >
                  {action.status}
                </span>
              </div>
              {action.result && <p className="mt-1 text-sm text-slate-600">{action.result}</p>}
            </Card>
          ))}
        </section>
      )}
    </div>
  )
}
