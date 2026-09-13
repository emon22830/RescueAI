import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Wordmark } from '../features/marketing/Wordmark'
import { useAuth } from '../lib/auth'
import { errorMessage } from '../lib/api'

/** Google's mark, unmodified, per their sign-in button guidelines — the one place in
 * this app an icon is not a single-colour stroke on the Icon.tsx grid. */
function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path
        fill="#4285F4"
        d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.47c-.28 1.5-1.13 2.78-2.4 3.63v3h3.88c2.27-2.09 3.57-5.17 3.57-8.82Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.88-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.27v3.11C3.25 21.3 7.31 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.27 14.28A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.56.38-2.28V6.61H1.27A11.98 11.98 0 0 0 0 12c0 1.94.46 3.77 1.27 5.39l4-3.11Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.35.61 4.6 1.8l3.44-3.44C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.27 6.61l4 3.11C6.22 6.87 8.87 4.77 12 4.77Z"
      />
    </svg>
  )
}

const PROMISES = [
  'Collection is read-only across every connected app.',
  'Findings always arrive with the evidence they cite.',
  'Nothing is written anywhere until you approve it.',
]

export function LoginPage() {
  const { session, loading, signInWithGoogle } = useAuth()
  const [signingIn, setSigningIn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Where RequireAuth turned them away from, if anywhere.
  const state = useLocation().state as { from?: string } | null
  const next = state?.from?.startsWith('/app') ? state.from : '/app'

  if (!loading && session) return <Navigate to={next} replace />

  async function handleSignIn() {
    setSigningIn(true)
    setError(null)
    try {
      // Redirects the browser to Google; there is nothing to do after this call
      // returns — the page navigates away, then back once Supabase has a session.
      await signInWithGoogle(next)
    } catch (caught) {
      setError(errorMessage(caught))
      setSigningIn(false)
    }
  }

  return (
    <div className="hero-sky flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <Link to="/" aria-label="RescueAI home">
        <Wordmark size="lg" />
      </Link>

      <Card className="mt-8 w-full max-w-sm p-8 shadow-float">
        <h1 className="text-xl font-extrabold tracking-tight">Sign in</h1>
        <p className="mt-1.5 text-sm text-muted">
          You will see the projects you own and the state the agent found them in.
        </p>

        {error && (
          <div className="mt-5">
            <Alert>{error}</Alert>
          </div>
        )}

        <Button
          variant="contrast"
          size="lg"
          loading={signingIn}
          onClick={handleSignIn}
          icon={!signingIn ? <GoogleMark /> : undefined}
          className="mt-6 w-full"
        >
          {signingIn ? 'Redirecting…' : 'Continue with Google'}
        </Button>

        <ul className="mt-7 space-y-2.5 border-t border-line pt-6">
          {PROMISES.map((promise) => (
            <li key={promise} className="flex gap-2.5 text-xs leading-relaxed text-muted">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand" aria-hidden />
              {promise}
            </li>
          ))}
        </ul>
      </Card>

      <Link
        to="/"
        className="mt-8 text-xs font-semibold text-muted transition-colors duration-150 hover:text-ink"
      >
        ← Back to the overview
      </Link>
    </div>
  )
}
