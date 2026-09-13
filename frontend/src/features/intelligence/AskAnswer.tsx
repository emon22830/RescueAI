import { useState } from 'react'

import { Icon } from '../../components/ui/Icon'
import { plural } from '../../lib/format'
import { AnswerText } from './AnswerText'
import { EvidenceItem } from './EvidenceItem'
import type { Answer } from './types'

/** One exchange in the thread. While `answer` is null the question is still in flight. */
export interface Exchange {
  id: number
  question: string
  answer: Answer | null
  error: string | null
}

interface Props {
  exchange: Exchange
  /** Asks a suggested follow-up as the next question in the thread. */
  onFollowUp: (question: string) => void
  /** The last exchange keeps its evidence open; earlier ones fold away. */
  latest: boolean
}

export function AskAnswer({ exchange, onFollowUp, latest }: Props) {
  const [showEvidence, setShowEvidence] = useState(false)
  const { answer, error } = exchange
  // A greeting or a question about the agent is not a hole in the evidence, so only a
  // real gap carries the warning.
  const gap = answer !== null && !answer.answered && answer.kind !== 'chat'

  return (
    <li className="space-y-3">
      <p className="flex gap-2.5 text-sm font-semibold">
        <span className="mt-0.5 shrink-0 text-faint" aria-hidden>
          <Icon.Search className="h-4 w-4" />
        </span>
        {exchange.question}
      </p>

      <div className="rounded-xl border border-line bg-raised p-4">
        {!answer && !error && (
          <div className="space-y-2.5" aria-live="polite">
            <p className="flex items-center gap-2 text-xs font-medium text-faint">
              <span className="h-1.5 w-1.5 animate-rescue-pulse rounded-full bg-brand" />
              Reading the collected evidence…
            </p>
            {/* The shape of the answer that is coming, not a bare "Loading…". `bg-line`
                rather than the shared Skeleton, which is `bg-raised` — the colour this
                bubble already is. */}
            <div className="h-3.5 w-full animate-rescue-pulse rounded bg-line" />
            <div className="h-3.5 w-11/12 animate-rescue-pulse rounded bg-line" />
            <div className="h-3.5 w-2/3 animate-rescue-pulse rounded bg-line" />
          </div>
        )}

        {error && <p className="text-sm text-danger">{error}</p>}

        {answer && (
          <>
            {gap && (
              <p className="mb-2.5 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.08em] text-warn">
                <Icon.Warning className="h-3.5 w-3.5" />
                Not in the evidence
              </p>
            )}

            <AnswerText text={answer.answer} />

            {answer.evidence.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={() => setShowEvidence(!showEvidence)}
                  aria-expanded={showEvidence}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface px-2.5 py-1.5 text-xs font-semibold transition-colors duration-150 hover:bg-raised"
                >
                  {showEvidence
                    ? 'Hide evidence'
                    : `Based on ${plural(answer.evidence.length, 'item')}`}
                  <Icon.Chevron
                    className={`h-3.5 w-3.5 transition-transform duration-200 ${
                      showEvidence ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {showEvidence && (
                  <ul className="mt-3 space-y-2.5">
                    {answer.evidence.map((item, index) => (
                      <EvidenceItem key={`${item.source}-${index}`} evidence={item} />
                    ))}
                  </ul>
                )}
              </>
            )}
          </>
        )}
      </div>

      {latest && answer && answer.follow_ups.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
            Ask next
          </span>
          {answer.follow_ups.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => onFollowUp(question)}
              className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors duration-150 hover:border-line-strong hover:text-ink"
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </li>
  )
}
