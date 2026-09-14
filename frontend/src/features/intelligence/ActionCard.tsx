import { ActionStatusBadge } from '../../components/ui/Badge'
import { SOURCE_LABELS, SourceAvatar } from '../../components/ui/SourceIcon'
import { dateTime, humanize } from '../../lib/format'
import type { Action, ActionStatus } from './types'

interface Props {
  action: Action
  /** The status to show — an action executing right now is not yet saved as such. */
  status: ActionStatus
  /** Present only while the action is still waiting for a decision. */
  selected?: boolean
  onToggle?: () => void
}

export function ActionCard({ action, status, selected, onToggle }: Props) {
  const selectable = status === 'pending' && onToggle !== undefined

  return (
    <div
      className={`rounded-xl border p-4 transition-colors duration-150 ${
        selectable && selected ? 'border-brand/40 bg-brand-soft/40' : 'border-line bg-surface'
      }`}
    >
      <div className="flex items-start gap-3.5">
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            aria-label={action.description}
            className="mt-1 h-4 w-4 shrink-0 accent-[var(--brand)]"
          />
        )}
        <SourceAvatar source={action.integration} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-sm font-medium leading-snug text-ink">{action.description}</p>
            <ActionStatusBadge status={status} />
          </div>

          <p className="mt-1.5 break-words text-xs text-faint">
            {/* Who wrote it. An action taken from the dashboard was never proposed by
                the agent, and the log should not imply that it was. */}
            {action.origin === 'user' ? 'You' : 'Agent'} · {SOURCE_LABELS[action.integration]} ·{' '}
            {humanize(action.type)}
            {action.target && (
              <>
                {' · '}
                <span className="font-medium text-muted">{action.target}</span>
              </>
            )}
          </p>

          {action.reason && (
            <p className="mt-2.5 text-sm text-muted">
              <span className="font-medium text-ink">Unblocks:</span> {action.reason}
            </p>
          )}

          {action.result && (
            <p
              className={`mt-3 break-words rounded-lg border px-3 py-2 text-sm ${
                status === 'failed'
                  ? 'border-danger/25 bg-danger-soft text-danger'
                  : 'border-line bg-raised text-muted'
              }`}
            >
              {action.result}
            </p>
          )}

          {action.executed_at && (
            <p className="mt-2 text-xs text-faint">Executed {dateTime(action.executed_at)}</p>
          )}
        </div>
      </div>
    </div>
  )
}
