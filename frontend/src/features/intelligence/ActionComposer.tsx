import { useState, type FormEvent } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Panel } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Icon } from '../../components/ui/Icon'
import { Skeleton } from '../../components/ui/Spinner'
import { api, errorMessage } from '../../lib/api'
import { ActionFields, ActionResult, INPUT } from './ActionFields'
import type { Action, ActionType } from './types'

/** Order the menu the way somebody thinks about the work, not alphabetically. */
const VERBS: { verb: string; label: string }[] = [
  { verb: 'add', label: 'Create' },
  { verb: 'update', label: 'Update' },
  { verb: 'delegate', label: 'Delegate' },
  { verb: 'close', label: 'Close' },
  { verb: 'message', label: 'Tell people' },
]

const keyOf = (entry: ActionType) => `${entry.integration}:${entry.type}`

/**
 * Act on a project without waiting for the agent to propose it.
 *
 * Writing the action *is* the approval — there is no second human left to ask — so it
 * runs on submit. It still becomes the same action row, in the same states, through the
 * same guard as anything the agent proposed, and it joins the list below with the rest.
 */
export function ActionComposer({
  projectId,
  types,
  loading,
  error,
  onDone,
}: {
  projectId: string
  types: ActionType[]
  loading: boolean
  error: string | null
  onDone: () => Promise<void>
}) {
  const [selected, setSelected] = useState('')
  const [target, setTarget] = useState('')
  const [value, setValue] = useState('')
  const [sending, setSending] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)
  const [done, setDone] = useState<Action | null>(null)

  const chosen = types.find((entry) => keyOf(entry) === selected) ?? null

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!chosen) return

    setSending(true)
    setFailed(null)
    setDone(null)
    try {
      const action = await api.createAction(projectId, {
        integration: chosen.integration,
        type: chosen.type,
        target,
        value,
      })
      setDone(action)
      setTarget('')
      setValue('')
      await onDone()
    } catch (caught) {
      setFailed(errorMessage(caught))
    } finally {
      setSending(false)
    }
  }

  return (
    <Panel title="Take an action" caption="Runs as soon as you send it">
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : error ? (
        <Alert tone="danger" title="Could not load what this project can do">
          {error}
        </Alert>
      ) : types.length === 0 ? (
        <EmptyState icon={<Icon.Plug className="h-5 w-5" />} title="No app to act on yet">
          Connect Slack, Linear, GitHub, Gmail or Calendar and everything you can do to it
          appears here — create, update, delegate, close, or tell the team.
        </EmptyState>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-muted">What to do</span>
            <select
              value={selected}
              onChange={(event) => {
                setSelected(event.target.value)
                setDone(null)
                setFailed(null)
              }}
              required
              className={INPUT}
            >
              <option value="">Choose an action…</option>
              {VERBS.filter(({ verb }) => types.some((entry) => entry.verb === verb)).map(
                ({ verb, label }) => (
                  <optgroup key={verb} label={label}>
                    {types
                      .filter((entry) => entry.verb === verb)
                      .map((entry) => (
                        <option key={keyOf(entry)} value={keyOf(entry)}>
                          {entry.label} · {entry.integration}
                        </option>
                      ))}
                  </optgroup>
                ),
              )}
            </select>
          </label>

          {chosen && (
            <ActionFields
              chosen={chosen}
              target={target}
              value={value}
              onTarget={setTarget}
              onValue={setValue}
            />
          )}

          {failed && (
            <Alert tone="danger" title="It did not go through">
              {failed}
            </Alert>
          )}
          {done && <ActionResult action={done} />}

          <Button type="submit" variant="primary" size="sm" loading={sending} disabled={!chosen}>
            {sending ? 'Sending…' : chosen ? chosen.label : 'Choose an action'}
          </Button>
        </form>
      )}
    </Panel>
  )
}
