import type { IncomingMessage } from 'node:http'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// 127.0.0.1, not localhost: Node resolves 'localhost' to ::1 first, and uvicorn
// binds IPv4 only, so an IPv6 target makes every proxied call ECONNREFUSED.
const API = 'http://127.0.0.1:8000'

/**
 * The app has a `/projects/:id` route *and* the API has a `/projects` path. Without a
 * bypass, opening or reloading the browser on a project page is proxied to FastAPI and
 * the user sees raw JSON. A request that accepts HTML is a page load, not an API call.
 */
function apiCallsOnly() {
  return {
    target: API,
    bypass: (req: IncomingMessage) =>
      req.headers.accept?.includes('text/html') ? '/index.html' : undefined,
  }
}

/**
 * Refuse to build an app that cannot sign anyone in.
 *
 * `supabaseClient.ts` throws at module top level when its two variables are missing.
 * In a production build Vite replaces `import.meta.env.VITE_*` with `undefined` before
 * minifying, so that throw becomes provably unconditional — and everything downstream
 * of it becomes dead code. The whole app tree-shakes away: the build exits 0, prints a
 * healthy-looking bundle a third of the usual size, and deploys a white screen. Nothing
 * about it reads as a failure, which is exactly what makes it dangerous.
 *
 * Only at build time. `vite dev` stays usable with a half-filled .env.
 */
function requireClientEnv(mode: string) {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const missing = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY'].filter(
    (name) => !env[name] && !process.env[name],
  )
  if (missing.length > 0) {
    throw new Error(
      `Cannot build: ${missing.join(' and ')} ${missing.length > 1 ? 'are' : 'is'} not set. ` +
        'Set them in frontend/.env locally, or in the hosting dashboard for a deployed ' +
        'build. Building without them silently produces an empty app.',
    )
  }
}

export default defineConfig(({ command, mode }) => {
  if (command === 'build') requireClientEnv(mode)

  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        // '/projects' also covers '/projects/{id}/integrations'.
        '/projects': apiCallsOnly(),
        '/health': apiCallsOnly(),
      },
    },
  }
})
