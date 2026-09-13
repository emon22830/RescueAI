import type { AgentRun, Project } from '../features/projects/types'
import type { Action, Finding } from '../features/intelligence/types'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listProjects: () => request<Project[]>('/projects'),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  createProject: (name: string, goal: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, goal }),
    }),

  analyzeProject: (id: string) =>
    request<AgentRun>(`/projects/${id}/analyze`, { method: 'POST' }),

  syncProject: (id: string) => request<AgentRun>(`/projects/${id}/sync`, { method: 'POST' }),

  getFindings: (id: string) => request<Finding[]>(`/projects/${id}/findings`),

  getRuns: (id: string) => request<AgentRun[]>(`/projects/${id}/runs`),

  getActions: (id: string) => request<Action[]>(`/projects/${id}/actions`),

  approveActions: (id: string, actionIds: string[]) =>
    request<Action[]>(`/projects/${id}/actions/approve`, {
      method: 'POST',
      body: JSON.stringify({ action_ids: actionIds }),
    }),
}
