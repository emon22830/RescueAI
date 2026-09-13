import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { Spinner } from '../components/ui/Spinner'
import { useAuth } from './auth'

/** Every route inside AppLayout needs a session — this is the one place that checks.
 * It only decides where the browser is allowed to navigate; whether a request actually
 * succeeds is still decided by the backend on every call, independent of this. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-6 w-6 text-muted" />
      </div>
    )
  }

  // Carry where they were going, so signing in returns them there and not to the
  // dashboard they did not ask for.
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }

  return <>{children}</>
}
