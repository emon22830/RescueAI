import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Card } from '../components/ui/Card'
import { HealthBadge } from '../components/ui/Badge'
import { CreateProjectForm } from '../features/projects/CreateProjectForm'
import type { Project } from '../features/projects/types'
import { api } from '../lib/api'

export function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((caught: Error) => setError(caught.message))
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>

      <CreateProjectForm onCreated={(project) => setProjects([project, ...projects])} />

      {error && <p className="text-sm text-red-700">{error}</p>}

      {projects.map((project) => (
        <Link key={project.id} to={`/projects/${project.id}`} className="block">
          <Card className="hover:border-slate-400">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-medium">{project.name}</h2>
                <p className="text-sm text-slate-600">{project.goal}</p>
              </div>
              {project.summary && <HealthBadge health={project.summary.health} />}
            </div>
          </Card>
        </Link>
      ))}

      {!error && projects.length === 0 && (
        <p className="text-sm text-slate-500">No projects yet. Create one above.</p>
      )}
    </div>
  )
}
