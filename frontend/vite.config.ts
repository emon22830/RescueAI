import type { IncomingMessage } from 'node:http'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

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

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // '/projects' also covers '/projects/{id}/integrations'.
      '/projects': apiCallsOnly(),
      '/health': apiCallsOnly(),
    },
  },
})
