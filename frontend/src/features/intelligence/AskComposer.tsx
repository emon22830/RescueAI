import { useEffect, useRef, type KeyboardEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'

/** Long enough to paste a paragraph of context in — the backend accepts the same. */
const MAX_LENGTH = 2000
/** The box opens at roughly four lines and grows to twelve before it scrolls, so a
 *  long question is written in full instead of through a letterbox. */
const MIN_HEIGHT = 88
const MAX_HEIGHT = 260

interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: (value: string) => void
  sending: boolean
  /** No project to ask about yet: the field explains that instead of failing on send. */
  ready: boolean
  /** Starter questions, shown only until the thread has something in it. */
  suggestions?: string[]
}

/**
 * The question field: one well, auto-sizing from four lines up, with the send control
 * inside it. The suggestions sit above so an empty panel still reads as a place to type.
 */
export function AskComposer({ value, onChange, onSubmit, sending, ready, suggestions }: Props) {
  const field = useRef<HTMLTextAreaElement>(null)

  // Re-measure on every change, including the reset to '' after a question is sent.
  useEffect(() => {
    const element = field.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(Math.max(element.scrollHeight, MIN_HEIGHT), MAX_HEIGHT)}px`
  }, [value])

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit(value)
    }
  }

  const remaining = MAX_LENGTH - value.length

  return (
    <div className="space-y-3">
      {suggestions && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={!ready || sending}
              onClick={() => onSubmit(suggestion)}
              className="rounded-full border border-line bg-raised px-3 py-1.5 text-xs font-medium text-muted transition-colors duration-150 hover:border-line-strong hover:text-ink disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-line-strong bg-surface transition-colors duration-150 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/20">
        <textarea
          ref={field}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          maxLength={MAX_LENGTH}
          disabled={!ready}
          style={{ minHeight: MIN_HEIGHT }}
          placeholder={
            ready
              ? 'Ask anything about this project — what is blocking it, what changed this week, who to chase. Paste in context if it helps.'
              : 'Create a project first'
          }
          // The well draws the focus state, so the field drops the global outline.
          className="block w-full resize-none bg-transparent px-3.5 pt-3.5 text-sm leading-6 text-ink placeholder:text-faint focus:outline-none disabled:cursor-not-allowed"
        />
        <div className="flex items-center justify-between gap-3 px-3 pb-3 pt-2">
          <span className="hidden text-[11px] text-faint tabular-nums sm:block">
            {remaining <= 200
              ? `${remaining} characters left`
              : 'Enter to send · Shift+Enter for a new line'}
          </span>
          <Button
            variant="primary"
            size="sm"
            loading={sending}
            disabled={!value.trim() || !ready}
            onClick={() => onSubmit(value)}
            icon={!sending ? <Icon.ArrowRight className="h-3.5 w-3.5" /> : undefined}
            className="ml-auto shadow-none"
          >
            Ask
          </Button>
        </div>
      </div>
    </div>
  )
}
