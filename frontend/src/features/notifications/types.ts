/** What the agent concluded while nobody was watching.
 *
 *  Written by a run, not by a user action — a scheduled analysis that changed a
 *  project's health, or one that failed. In-app only: telling somebody their project
 *  is at risk is not a reason to write into their Slack without approval.
 */
export type NotificationKind = 'health_changed' | 'blockers_found' | 'run_failed'

export interface Notification {
  id: string
  project_id: string
  run_id: string | null
  kind: NotificationKind
  severity: 'info' | 'warn' | 'danger'
  title: string
  body: string
  read_at: string | null
  created_at: string
}
