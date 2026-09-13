import { useState, type FormEvent } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Panel } from '../../components/ui/Card'
import { api, errorMessage } from '../../lib/api'
import type { Project } from './types'

const INPUT =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-faint transition-colors duration-150 focus:border-brand'

export function CreateProjectForm({ onCreated }: { onCreated: (project: Project) => void }) {
  const [name, setName] = useState('')
  const [goal, setGoal] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      onCreated(await api.createProject(name.trim(), goal.trim()))
      setName('')
      setGoal('')
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel
      title="Track a project"
      caption="The name is what the agent searches the connected apps for."
    >
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-muted">Project name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="SaaS Product Launch"
              required
              maxLength={200}
              className={INPUT}
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-muted">Goal</span>
            <input
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="Launch the product by Oct 1"
              required
              maxLength={500}
              className={INPUT}
            />
          </label>
        </div>

        {error && <Alert>{error}</Alert>}

        <Button type="submit" variant="primary" loading={saving} className="w-full sm:w-auto">
          {saving ? 'Creating…' : 'Create project'}
        </Button>
      </form>
    </Panel>
  )
}
