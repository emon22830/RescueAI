import { useState } from 'react'

import { Card } from '../../components/ui/Card'
import { api } from '../../lib/api'
import type { Project } from './types'

export function CreateProjectForm({ onCreated }: { onCreated: (project: Project) => void }) {
  const [name, setName] = useState('')
  const [goal, setGoal] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      onCreated(await api.createProject(name, goal))
      setName('')
      setGoal('')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create the project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <h2 className="font-medium">New project</h2>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="SaaS Product Launch"
          required
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="Launch the product by Oct 1"
          required
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? 'Creating…' : 'Create project'}
        </button>
        {error && <p className="text-sm text-red-700">{error}</p>}
      </form>
    </Card>
  )
}
