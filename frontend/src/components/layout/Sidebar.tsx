import { NavLink } from 'react-router-dom'

import { Icon } from '../ui/Icon'
import { Skeleton } from '../ui/Spinner'
import type { Health, Project } from '../../features/projects/types'

const HEALTH_DOT: Record<Health, string> = {
  on_track: 'bg-success',
  watch: 'bg-warn',
  at_risk: 'bg-danger',
}

function itemClass(isActive: boolean): string {
  return `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold transition-colors duration-150 ${
    isActive ? 'bg-brand-soft text-brand-soft-ink' : 'text-muted hover:bg-raised hover:text-ink'
  }`
}

/** One project, and — when it is the one you are looking at — the pages inside it. */
function ProjectItem({ project, expanded }: { project: Project; expanded: boolean }) {
  return (
    <li>
      <NavLink to={`/app/projects/${project.id}`} end className={({ isActive }) => itemClass(isActive)}>
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${HEALTH_DOT[project.summary.health]}`}
          aria-hidden
        />
        <span className="truncate">{project.name}</span>
      </NavLink>

      {expanded && (
        <ul className="mt-0.5 ml-[1.4rem] border-l border-line pl-2.5">
          <li>
            <NavLink
              to={`/app/projects/${project.id}`}
              end
              className={({ isActive }) => itemClass(isActive)}
            >
              <Icon.Activity className="h-4 w-4 shrink-0" />
              Overview
            </NavLink>
          </li>
          <li>
            <NavLink
              to={`/app/projects/${project.id}/connections`}
              className={({ isActive }) => itemClass(isActive)}
            >
              <Icon.Plug className="h-4 w-4 shrink-0" />
              Connections
            </NavLink>
          </li>
        </ul>
      )}
    </li>
  )
}

export function Sidebar({
  projects,
  loading,
  activeProjectId,
  onNavigate,
}: {
  projects: Project[]
  loading: boolean
  /** Which project's sub-pages to expand, from the URL. */
  activeProjectId: string | null
  /** Closes the mobile drawer after a link is followed. */
  onNavigate: () => void
}) {
  return (
    <nav className="flex h-full flex-col gap-6 overflow-y-auto p-4" onClick={onNavigate}>
      <ul>
        <li>
          <NavLink to="/app" end className={({ isActive }) => itemClass(isActive)}>
            <Icon.Layers className="h-4 w-4 shrink-0" />
            Overview
          </NavLink>
        </li>
      </ul>

      <div>
        <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-[0.1em] text-faint">
          Projects
        </p>

        {loading && (
          <div className="space-y-1.5 px-1">
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} className="h-8 w-full" />
            ))}
          </div>
        )}

        {!loading && projects.length === 0 && (
          <p className="px-3 text-xs leading-relaxed text-faint">
            No projects yet. Create one to start investigating.
          </p>
        )}

        <ul className="space-y-0.5">
          {projects.map((project) => (
            <ProjectItem
              key={project.id}
              project={project}
              expanded={project.id === activeProjectId}
            />
          ))}
        </ul>

        <NavLink to="/app?new=1" className={() => itemClass(false)}>
          <Icon.Plus className="h-4 w-4 shrink-0" />
          New project
        </NavLink>
      </div>
    </nav>
  )
}
