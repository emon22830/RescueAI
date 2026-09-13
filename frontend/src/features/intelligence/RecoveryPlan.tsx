import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Panel } from '../../components/ui/Card'
import { Icon } from '../../components/ui/Icon'
import { SOURCE_LABELS } from '../../components/ui/SourceIcon'
import { plural } from '../../lib/format'
import { ActionCard } from './ActionCard'
import type { Action } from './types'

/**
 * The only screen in the product that can change somebody else's workspace. It says
 * what will be written and where before it offers the button.
 */
export function RecoveryPlan({
  pending,
  selected,
  executing,
  busy,
  onToggle,
  onApprove,
}: {
  pending: Action[]
  selected: string[]
  /** Ids in flight — approve is synchronous, so this is what shows Executing. */
  executing: string[]
  busy: boolean
  onToggle: (id: string) => void
  onApprove: () => void
}) {
  const targets = [...new Set(pending.map((action) => SOURCE_LABELS[action.integration]))]
  const count = selected.length

  return (
    <Panel
      title="Recovery plan"
      caption={`${plural(pending.length, 'step')} proposed by the agent`}
      bodyClassName="p-5 space-y-4"
    >
      <Alert tone="info">
        Approving writes to {targets.join(', ')}. Nothing is sent until you press the button,
        and unchecked steps are never executed.
      </Alert>

      <div className="space-y-3">
        {pending.map((action) => (
          <ActionCard
            key={action.id}
            action={action}
            status={executing.includes(action.id) ? 'executing' : 'pending'}
            selected={selected.includes(action.id)}
            onToggle={() => onToggle(action.id)}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <p className="text-xs text-faint">
          {count === 0
            ? 'Select at least one step to approve.'
            : `${plural(count, 'step')} selected of ${pending.length}.`}
        </p>
        <Button
          variant="primary"
          loading={busy}
          disabled={count === 0}
          onClick={onApprove}
          icon={<Icon.Check className="h-4 w-4" />}
        >
          {busy ? 'Executing…' : `Approve & execute ${plural(count, 'action')}`}
        </Button>
      </div>
    </Panel>
  )
}
