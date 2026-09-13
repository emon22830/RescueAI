import { Card } from '../../components/ui/Card'
import { ActionStatusBadge } from '../../components/ui/Badge'
import type { Action, ActionStatus } from './types'

interface Props {
  action: Action
  /** The status to show — an action being executed right now is not yet saved as such. */
  status: ActionStatus
  /** Present only while the action is still waiting for a decision. */
  selected?: boolean
  onToggle?: () => void
}

export function ActionCard({ action, status, selected, onToggle }: Props) {
  const pending = status === 'pending'

  return (
    <Card>
      <div className="flex items-start gap-3">
        {pending && onToggle && (
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            aria-label={action.description}
            className="mt-1 h-4 w-4"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-medium">{action.description}</p>
            <ActionStatusBadge status={status} />
          </div>

          <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
            {action.integration} · {action.type}
            {action.target && ` · ${action.target}`}
          </div>

          {action.reason && (
            <p className="mt-2 text-sm text-slate-600">
              <span className="font-medium">Why:</span> {action.reason}
            </p>
          )}

          {action.result && (
            <p
              className={`mt-2 text-sm ${
                status === 'failed' ? 'text-red-700' : 'text-slate-600'
              }`}
            >
              {action.result}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}
