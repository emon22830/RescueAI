import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'

import { AppLayout } from './components/layout/AppLayout'
import { AuthProvider } from './lib/auth'
import { RequireAuth } from './lib/RequireAuth'
import { ConnectionsPage } from './pages/ConnectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectPage } from './pages/ProjectPage'

/** `/` is the public landing page; everything the agent actually does lives under
 *  `/app` behind a session. Connections hang off a project because that is where the
 *  backend stores them — one project's Slack token is not another's. */
export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/app"
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="projects/:projectId" element={<ProjectPage />} />
            <Route path="projects/:projectId/connections" element={<ConnectionsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}
