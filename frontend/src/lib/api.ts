import type { ConnectIntegrationBody, IntegrationStatus } from '../features/integrations/types'
import type { Action, ActionType, Answer, Finding } from '../features/intelligence/types'
import type { Notification } from '../features/notifications/types'
import type { AgentRun, Project } from '../features/projects/types'
import { supabase } from './supabaseClient'

const BASE = import.meta.env.VITE_API_URL ?? ''

/** What the API said went wrong, in the words a user can act on. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** One refresh at a time.
 *
 * A page opens several requests at once, so an expired token fails several of them at
 * once. Refreshing per failure would race: Supabase rotates the refresh token, the
 * first call consumes it and the rest present one that no longer exists, which ends a
 * session that only needed renewing. They all wait on the same refresh instead.
 */
let refreshing: Promise<string | null> | null = null

function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = supabase.auth
      .refreshSession()
      .then(({ data }) => data.session?.access_token ?? null)
      .catch(() => null)
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

async function send(path: string, token: string | null, options?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BASE}${path}`, {
      ...options,
      // After the spread, never before it — a caller's `headers` must not be able to
      // drop the Authorization header and turn an ordinary call into an anonymous one.
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    })
  } catch {
    // fetch only rejects before a response exists: the host is unreachable, or the
    // browser blocked the response because it carried no CORS headers. The deployed
    // app is the second case far more often, and "port 8000" is a lie there — so name
    // the host that actually failed.
    throw new ApiError(
      0,
      BASE
        ? `Could not reach the backend at ${BASE}. It may be starting up, or it is not ` +
          `allowing requests from ${window.location.origin} (backend CORS_ORIGINS).`
        : 'Could not reach the backend. Is it running on port 8000?',
    )
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // The backend decides who a user is and what they can reach — every call proves who
  // is asking with the current Supabase session token. Nothing here reads or acts on
  // the token; it is only ever attached and handed off.
  const { data } = await supabase.auth.getSession()
  let response = await send(path, data.session?.access_token ?? null, options)

  if (response.status === 401) {
    // getSession() hands back whatever is cached, and the backend may have stopped
    // accepting it — it expired while the tab sat open, or another tab rotated it.
    // One forced refresh separates a token that needs renewing from a session that is
    // really gone.
    const token = await refreshAccessToken()
    if (token) response = await send(path, token, options)

    if (response.status === 401) {
      // Really gone. Ending it here is what makes the app recover: the session goes
      // null, RequireAuth sends the user to sign in and brings them back to this page.
      // Left in place, every screen shows "Invalid or expired session" until the user
      // works out that the fix is to sign out by hand.
      await supabase.auth.signOut()
    }
  }

  if (!response.ok) {
    // The handlers in main.py all answer {"detail": "..."} — show that, not the body.
    const body = await response.text()
    let detail = body
    try {
      detail = (JSON.parse(body).detail as string) ?? body
    } catch {
      /* not JSON — the raw text is the best we have */
    }
    throw new ApiError(response.status, detail || `${response.status} on ${path}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  listProjects: () => request<Project[]>('/projects'),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),

  createProject: (name: string, goal: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, goal }),
    }),

  /** Both of these return a *queued* run — the work happens on the server afterwards.
   *  Poll getRuns until that run's status leaves 'queued' and 'running'. */
  analyzeProject: (id: string) =>
    request<AgentRun>(`/projects/${id}/analyze`, { method: 'POST' }),

  syncProject: (id: string) => request<AgentRun>(`/projects/${id}/sync`, { method: 'POST' }),

  /** Minutes between automatic re-analyses, or null to turn monitoring off. */
  setSchedule: (id: string, minutes: number | null) =>
    request<Project>(`/projects/${id}/schedule`, {
      method: 'PUT',
      body: JSON.stringify({ sync_interval_minutes: minutes }),
    }),

  getFindings: (id: string) => request<Finding[]>(`/projects/${id}/findings`),

  getRuns: (id: string) => request<AgentRun[]>(`/projects/${id}/runs`),

  getActions: (id: string) => request<Action[]>(`/projects/${id}/actions`),

  /** What this project can be asked to do, given the apps it has connected. */
  getActionTypes: (id: string) => request<ActionType[]>(`/projects/${id}/actions/types`),

  /** Take one action directly, without waiting for the agent to propose it. Writing it
   *  is the approval, so it runs in this request and comes back with its result. */
  createAction: (
    id: string,
    body: { integration: string; type: string; target: string; value: string },
  ) =>
    request<Action>(`/projects/${id}/actions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  approveActions: (id: string, actionIds: string[]) =>
    request<Action[]>(`/projects/${id}/actions/approve`, {
      method: 'POST',
      body: JSON.stringify({ action_ids: actionIds }),
    }),

  /** Ask a question about one project. The backend answers only from the evidence its
   *  latest completed run collected, and cites what it used. */
  askProject: (id: string, question: string) =>
    request<Answer>(`/projects/${id}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  // Integrations belong to a project: one project's Slack token is not another's.
  listIntegrations: (projectId: string) =>
    request<IntegrationStatus[]>(`/projects/${projectId}/integrations`),

  connectIntegration: (projectId: string, provider: string, body: ConnectIntegrationBody) =>
    request<IntegrationStatus>(`/projects/${projectId}/integrations/${provider}/connect`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Google is granted, not pasted: this returns the consent screen to send the
  // browser to. The backend handles the redirect back and stores the grant.
  googleAuthorizeUrl: (projectId: string) =>
    request<{ url: string }>(`/projects/${projectId}/integrations/google/authorize`),

  disconnectIntegration: (projectId: string, provider: string) =>
    request<void>(`/projects/${projectId}/integrations/${provider}`, { method: 'DELETE' }),

  // What the agent decided while the user was away. Not scoped to a project: the
  // point is to surface the project you were not looking at.
  listNotifications: (unreadOnly = false) =>
    request<Notification[]>(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),

  markNotificationsRead: (ids: string[]) =>
    request<Notification[]>('/notifications/read', {
      method: 'POST',
      body: JSON.stringify({ notification_ids: ids }),
    }),
}

/** Every catch block in the app funnels through this, so no raw Error reaches the UI. */
export function errorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : 'Something went wrong'
}
