import { useState } from 'react'

import { Badge } from '../../components/ui/Badge'
import { Panel } from '../../components/ui/Card'
import { Icon } from '../../components/ui/Icon'
import { timeAgo } from '../../lib/format'
import type { Project } from './types'

/** The intervals worth offering. Below 15 minutes costs more in API calls than it
 *  buys in freshness — the backend refuses anything faster. */
const INTERVALS: { minutes: number | null; label: string }[] = [
  { minutes: null, label: 'Manual only' },
  { minutes: 60, label: 'Hourly' },
  { minutes: 360, label: 'Every 6 hours' },
  { minutes: 1440, label: 'Daily' },
]

function labelFor(minutes: number | null): string {
  return INTERVALS.find((option) => option.minutes === minutes)?.label ?? `Every ${minutes}m`
}

/** Continuous monitoring for one project: how often the agent re-investigates on its
 *  own. Collecting is read-only, so a schedule never writes anything — the recovery
 *  plan it produces still waits for approval like any other. */
export function MonitoringCard({
  project,
  onChange,
}: {
  project: Project
  onChange: (minutes: number | null) => Promise<void>
}) {
  const [saving, setSaving] = useState<number | null | undefined>(undefined)
  const current = project.sync_interval_minutes
  const on = current !== null

  async function choose(minutes: number | null) {
    if (minutes === current) return
    setSaving(minutes)
    try {
      await onChange(minutes)
    } finally {
      setSaving(undefined)
    }
  }

  return (
    <Panel
      title="Monitoring"
      caption={on ? `Re-investigating ${labelFor(current).toLowerCase()}` : 'Runs only when you ask'}
      action={
        <Badge tone={on ? 'success' : 'neutral'}>
          <Icon.Clock className="h-3.5 w-3.5" />
          {on ? 'On' : 'Off'}
        </Badge>
      }
    >
      <div className="flex flex-wrap gap-2">
        {INTERVALS.map((option) => {
          const active = option.minutes === current
          return (
            <button
              key={option.label}
              type="button"
              disabled={saving !== undefined}
              onClick={() => void choose(option.minutes)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors duration-150 disabled:opacity-50 ${
                active
                  ? 'border-brand bg-brand-soft text-brand'
                  : 'border-line text-muted hover:border-line-strong hover:text-ink'
              }`}
            >
              {saving === option.minutes ? 'Saving…' : option.label}
            </button>
          )
        })}
      </div>

      <p className="mt-4 text-xs text-faint">
        {on ? (
          <>
            Last checked {timeAgo(project.last_synced_at)}. Each run collects read-only and
            notifies you if the verdict changes — the recovery plan it writes still waits for
            your approval.
          </>
        ) : (
          <>
            Nothing runs against your connected apps unless you press Run analysis. Turn this on
            and the agent re-checks on its own, and tells you when the verdict changes.
          </>
        )}
      </p>
    </Panel>
  )
}
