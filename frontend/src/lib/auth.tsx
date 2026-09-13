import type { Session } from '@supabase/supabase-js'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { supabase } from './supabaseClient'

/** The signed-in session, or null. This is the only state this file holds — it does not
 * decide what a signed-in user is allowed to do. That is entirely the backend's call,
 * made fresh on every request from the bearer token api.ts attaches.
 */
interface AuthState {
  session: Session | null
  loading: boolean
  /** `next` is the in-app path to land on after Google returns; defaults to the app. */
  signInWithGoogle: (next?: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    // Fires on sign-in, sign-out, and token refresh — the token api.ts sends is always
    // the current one, never one captured once and going stale.
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
    })
    return () => subscription.subscription.unsubscribe()
  }, [])

  async function signInWithGoogle(next = '/app') {
    // Google returns the browser to this exact URL. Sending it to the origin landed the
    // user back on the public landing page still needing a click to reach the app.
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: new URL(next, window.location.origin).toString() },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{ session, loading, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
