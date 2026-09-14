import { useCallback, useEffect, useState } from 'react'

import { Icon } from '../../components/ui/Icon'
import { api, errorMessage } from '../../lib/api'
import { NotificationList } from './NotificationList'
import type { Notification } from './types'

/** How often the shell re-checks. Scheduled runs are hourly at their fastest, so a
 *  minute is already far finer than anything they can report. */
const POLL_MS = 60_000

/** What the agent decided while the user was away. The only thing in the app that
 *  appears without someone asking for it, so it stays quiet until there is news. */
export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const load = useCallback(async () => {
    try {
      setNotifications(await api.listNotifications())
      setError(null)
    } catch (caught) {
      setError(errorMessage(caught))
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = setInterval(() => void load(), POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const unread = notifications.filter((item) => item.read_at === null)

  async function markAllRead() {
    if (unread.length === 0) return
    setNotifications(await api.markNotificationsRead(unread.map((item) => item.id)))
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={unread.length ? `${unread.length} unread notifications` : 'Notifications'}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-raised hover:text-ink"
      >
        <Icon.Bell className="h-5 w-5" />
        {unread.length > 0 && (
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger ring-2 ring-surface" />
        )}
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Close notifications"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-30 cursor-default"
          />
          <div className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-line bg-surface shadow-float">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <span className="text-sm font-semibold">Notifications</span>
              {unread.length > 0 && (
                <button
                  type="button"
                  onClick={() => void markAllRead()}
                  className="text-xs font-medium text-brand transition-colors duration-150 hover:underline"
                >
                  Mark all read
                </button>
              )}
            </div>

            <div className="max-h-96 overflow-y-auto">
              <NotificationList
                notifications={notifications}
                error={error}
                onOpen={() => setOpen(false)}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
