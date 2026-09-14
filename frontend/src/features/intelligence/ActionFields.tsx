import { Alert } from '../../components/ui/Alert'
import { SourceIcon } from '../../components/ui/SourceIcon'
import type { Action, ActionType } from './types'

export const INPUT =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-faint transition-colors duration-150 focus:border-brand'

/** The two fields every action has, labelled in that action's own words rather than
 *  as "target" and "value" — those are our names for them, not the user's. */
export function ActionFields({
  chosen,
  target,
  value,
  onTarget,
  onValue,
}: {
  chosen: ActionType
  target: string
  value: string
  onTarget: (next: string) => void
  onValue: (next: string) => void
}) {
  return (
    <>
      <label className="block">
        <span className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-muted">
          <SourceIcon source={chosen.integration} className="h-3.5 w-3.5" />
          {chosen.target_label}
        </span>
        <input
          value={target}
          onChange={(event) => onTarget(event.target.value)}
          required
          className={INPUT}
        />
      </label>

      <label className="block">
        <span className="mb-1.5 block text-xs font-semibold text-muted">{chosen.value_label}</span>
        <textarea
          value={value}
          onChange={(event) => onValue(event.target.value)}
          rows={3}
          className={`${INPUT} resize-y`}
        />
      </label>
    </>
  )
}

/** What the app said back — verbatim, the same line the action list shows. */
export function ActionResult({ action }: { action: Action }) {
  const failed = action.status === 'failed'
  return (
    <Alert tone={failed ? 'danger' : 'success'} title={failed ? 'It failed' : 'Done'}>
      {action.result ?? (failed ? 'The app gave no reason.' : 'The app accepted it.')}
    </Alert>
  )
}
