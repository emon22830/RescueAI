import { useCallback, useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'
import { Wordmark } from '../../features/marketing/Wordmark'
import type { Project } from '../../features/projects/types'
import { api, errorMessage } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import type { AppData } from '../../lib/appData'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'

/** Which project the sidebar should expand, read straight from the URL. */
function activeProjectFrom(pathname: string): string | null {
  return pathname.match(/^\/app\/projects\/([^/]+)/)?.[1] ?? null
}

export function AppLayout() {
  const { pathname } = useLocation()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const reload = useCallback(async () => {
    setError(null)
    try {
      setProjects(await api.listProjects())
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  // A route change closes the drawer; otherwise it hides the page you just opened.
  useEffect(() => setDrawerOpen(false), [pathname])

  const data: AppData = { projects, loading, error, reload }
  const activeProjectId = activeProjectFrom(pathname)

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Sidebar
          projects={projects}
          loading={loading}
          activeProjectId={activeProjectId}
          onNavigate={() => setDrawerOpen(false)}
        />
      </MobileDrawer>

      <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-16 shrink-0 items-center border-b border-line px-5">
          <Link to="/app" aria-label="Overview">
            <Wordmark />
          </Link>
        </div>
        <div className="min-h-0 flex-1">
          <Sidebar
            projects={projects}
            loading={loading}
            activeProjectId={activeProjectId}
            onNavigate={() => {}}
          />
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur-md">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open navigation"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-raised hover:text-ink lg:hidden"
            >
              <Icon.Menu className="h-5 w-5" />
            </button>

            <Link to="/app" className="lg:hidden" aria-label="Overview">
              <Wordmark />
            </Link>

            <div className="ml-auto flex items-center gap-2">
              <ThemeToggle />
              <UserMenu />
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <Outlet context={data} />
          </div>
        </main>

        <footer className="px-4 pb-10 sm:px-6 lg:px-8">
          <p className="mx-auto max-w-6xl text-xs text-faint">
            Evidence is collected read-only. Nothing is written to a connected app until you
            approve it.
          </p>
        </footer>
      </div>
    </div>
  )
}

function MobileDrawer({
  open,
  onClose,
  children,
}: {
  open: boolean
  onClose: () => void
  children: React.ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <button
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
        className="absolute inset-0 bg-contrast/40"
      />
      <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-line bg-surface shadow-float">
        <div className="flex h-16 shrink-0 items-center border-b border-line px-5">
          <Wordmark />
        </div>
        <div className="min-h-0 flex-1">{children}</div>
      </div>
    </div>
  )
}

/** Who is signed in, and the way out. The email is the only identity we have. */
function UserMenu() {
  const { session, signOut } = useAuth()
  const email = session?.user.email

  return (
    <div className="flex items-center gap-2">
      {email && (
        <span className="hidden max-w-[14rem] truncate text-xs text-faint sm:inline">{email}</span>
      )}
      <Button variant="ghost" size="sm" onClick={() => void signOut()}>
        Sign out
      </Button>
    </div>
  )
}
