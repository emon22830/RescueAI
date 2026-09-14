import { Link } from 'react-router-dom'

import { timeAgo } from '../../lib/format'
import type { Notification } from './types'

const TONE: Record<Notification['severity'], string> = {
  danger: 'bg-danger',
  warn: 'bg-warn',
  info: 'bg-brand',
}

/** The contents of the notification panel — all four states of it. */
export function NotificationList({
  notifications,
  error,
  onOpen,
}: {
  notifications: Notification[]
  error: string | null
  onOpen: () => void
}) {
  if (error) return <p className="px-4 py-6 text-sm text-muted">{error}</p>

  if (notifications.length === 0) {
    return (
      <p className="px-4 py-6 text-sm text-muted">
        Nothing yet. Turn monitoring on for a project and the agent will tell you here when its
        verdict changes.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-line">
      {notifications.map((item) => (
        <li key={item.id}>
          <Link
            to={`/app/projects/${item.project_id}`}
            onClick={onOpen}
            className="flex gap-3 px-4 py-3 transition-colors duration-150 hover:bg-raised"
          >
            <span
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                item.read_at ? 'bg-line-strong' : TONE[item.severity]
              }`}
            />
            <span className="min-w-0">
              <span className="block text-sm font-medium text-ink">{item.title}</span>
              {item.body && <span className="mt-0.5 block text-xs text-muted">{item.body}</span>}
              <span className="mt-1 block text-xs text-faint">{timeAgo(item.created_at)}</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
