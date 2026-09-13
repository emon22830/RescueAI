import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'

import { AppLayout } from './components/layout/AppLayout'
import { ConnectionsPage } from './pages/ConnectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectPage } from './pages/ProjectPage'

export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects/:projectId" element={<ProjectPage />} />
          <Route path="/connections" element={<ConnectionsPage />} />
        </Route>
      </Routes>
    </Router>
  )
}
