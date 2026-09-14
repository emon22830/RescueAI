import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

/** The Supabase client is the one thing api.ts talks to besides fetch. Mocking it is
 *  what lets these tests drive an expired session without a real one. */
const getSession = vi.fn()
const refreshSession = vi.fn()
const signOut = vi.fn()

vi.mock('./supabaseClient', () => ({
  supabase: { auth: { getSession, refreshSession, signOut } },
}))

const { api, ApiError } = await import('./api')

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function authHeader(call: number): string | undefined {
  const init = vi.mocked(globalThis.fetch).mock.calls[call][1] as RequestInit
  return (init.headers as Record<string, string>).Authorization
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  getSession.mockResolvedValue({ data: { session: { access_token: 'current-token' } } })
  refreshSession.mockResolvedValue({ data: { session: { access_token: 'fresh-token' } } })
  signOut.mockResolvedValue(undefined)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.clearAllMocks()
})

describe('the session a request carries', () => {
  it('proves who is asking with the current token', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(jsonResponse(200, []))

    await api.listProjects()

    expect(authHeader(0)).toBe('Bearer current-token')
  })

  it('renews a token the backend has stopped accepting, and retries', async () => {
    vi.mocked(globalThis.fetch)
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'Invalid or expired session' }))
      .mockResolvedValueOnce(jsonResponse(200, [{ id: 'p1' }]))

    const projects = await api.listProjects()

    expect(refreshSession).toHaveBeenCalledTimes(1)
    expect(authHeader(1)).toBe('Bearer fresh-token')
    expect(projects).toEqual([{ id: 'p1' }])
    expect(signOut).not.toHaveBeenCalled()
  })

  it('ends a session that is really gone, so the app can recover', async () => {
    // Left signed in, every screen shows "Invalid or expired session" until the user
    // works out that the fix is to sign out by hand. Signing out sends them to /login
    // and back to the page they were on.
    vi.mocked(globalThis.fetch).mockResolvedValue(
      jsonResponse(401, { detail: 'Invalid or expired session' }),
    )

    await expect(api.listProjects()).rejects.toThrow(ApiError)
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('refreshes once for a page that fails several requests at once', async () => {
    // The reason the refresh is shared. Supabase rotates the refresh token, so a
    // refresh per failed request means the first consumes it and the rest present one
    // that no longer exists — ending a session that only needed renewing.
    vi.mocked(globalThis.fetch).mockImplementation(async (_url, init) => {
      const header = (init?.headers as Record<string, string>).Authorization
      return header === 'Bearer fresh-token'
        ? jsonResponse(200, [])
        : jsonResponse(401, { detail: 'Invalid or expired session' })
    })

    await Promise.all([api.listProjects(), api.listProjects(), api.listProjects()])

    expect(refreshSession).toHaveBeenCalledTimes(1)
    expect(signOut).not.toHaveBeenCalled()
  })

  it('does not sign out over an error that is not about the session', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(jsonResponse(500, { detail: 'boom' }))

    await expect(api.listProjects()).rejects.toThrow('boom')
    expect(refreshSession).not.toHaveBeenCalled()
    expect(signOut).not.toHaveBeenCalled()
  })
})

describe('what the user is told when a call fails', () => {
  it('passes on the reason the API gave', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(jsonResponse(404, { detail: 'No such project' }))

    await expect(api.getProject('nope')).rejects.toThrow('No such project')
  })

  // BASE is read once at module load, so each of these re-imports api.ts under a
  // different VITE_API_URL rather than sharing the instance the other tests use.
  async function apiBuiltWith(base: string | undefined) {
    vi.resetModules()
    if (base === undefined) vi.stubEnv('VITE_API_URL', '')
    else vi.stubEnv('VITE_API_URL', base)
    return (await import('./api')).api
  }

  it('names the host that could not be reached, not a local port', async () => {
    // A deployed app blaming port 8000 sends people to look at the wrong machine.
    const deployed = await apiBuiltWith('https://api.example.com')
    vi.mocked(globalThis.fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(deployed.listProjects()).rejects.toThrow(/api\.example\.com/)
    await expect(deployed.listProjects()).rejects.toThrow(/CORS_ORIGINS/)
  })

  it('still points at the local port when there is no deployed backend', async () => {
    const local = await apiBuiltWith(undefined)
    vi.mocked(globalThis.fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(local.listProjects()).rejects.toThrow(/port 8000/)
  })
})
