import { createClient } from '@supabase/supabase-js'

/** The one thing this file is for: signing in and holding the session.
 *
 * This client never reads or writes application data — no project, no finding, no
 * action ever comes from here. All of that goes through lib/api.ts to our own backend,
 * which is the only place authorization is decided. This client's only job is the part
 * that must happen in the browser: send the user to Google, catch the redirect back,
 * and hand us the resulting access token so api.ts can attach it to every request.
 */

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url || !anonKey) {
  // Loud on purpose: a silently-missing key means every sign-in attempt fails with no
  // clue why. See frontend/.env.example.
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Copy frontend/.env.example to ' +
      'frontend/.env and fill them in from the Supabase dashboard (Project Settings → API).',
  )
}

export const supabase = createClient(url, anonKey)
