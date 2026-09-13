import { useOutletContext } from 'react-router-dom'

import type { Project } from '../features/projects/types'

/**
 * The project list, loaded once by AppLayout and shared with every page under it.
 *
 * The sidebar and the dashboard show the same list, so fetching it twice would mean
 * they could disagree — creating a project would appear in one and not the other.
 * React Router's outlet context is enough to share it; there is no state library here.
 */
export interface AppData {
  projects: Project[]
  loading: boolean
  error: string | null
  /** Re-read the list from the API — after creating a project, or after a sync. */
  reload: () => Promise<void>
}

export function useAppData(): AppData {
  return useOutletContext<AppData>()
}
