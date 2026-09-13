import { useState } from 'react'

import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import type { Source } from '../intelligence/types'
import { Section } from './Section'

interface UseCase {
  title: string
  body: string
  signals: { source: Source; looks_for: string }[]
}

const USE_CASES: UseCase[] = [
  {
    title: 'Launch programs',
    body: 'A dated goal with a dozen dependencies and one thread that quietly changed the plan.',
    signals: [
      { source: 'calendar', looks_for: 'A review dated before the blocker can clear' },
      { source: 'gmail', looks_for: 'A requirement changed after work started' },
      { source: 'linear', looks_for: 'Issues overdue against the launch date' },
    ],
  },
  {
    title: 'Agency and client delivery',
    body: 'What the client was promised in email versus what is actually on the board.',
    signals: [
      { source: 'gmail', looks_for: 'Scope agreed outside the tracker' },
      { source: 'drive', looks_for: 'The statement of work that superseded the last one' },
      { source: 'linear', looks_for: 'Work with no owner as the date approaches' },
    ],
  },
  {
    title: 'Platform migrations',
    body: 'Long-running work where the spec and the code drift apart quietly for weeks.',
    signals: [
      { source: 'github', looks_for: 'Branches with no commits since the spec changed' },
      { source: 'drive', looks_for: 'A design doc newer than the implementation' },
      { source: 'slack', looks_for: 'Repeated questions nobody has answered' },
    ],
  },
  {
    title: 'Projects you inherited',
    body: 'Somebody handed you this last week and the status report is six weeks old.',
    signals: [
      { source: 'slack', looks_for: 'Where the conversation actually stopped' },
      { source: 'linear', looks_for: 'What is genuinely in flight versus parked' },
      { source: 'github', looks_for: 'The last thing anyone shipped' },
    ],
  },
]

export function UseCases() {
  const [active, setActive] = useState(0)
  const current = USE_CASES[active]

  return (
    <Section id="use-cases">
      <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-brand">
            Use cases
          </span>
          <h2 className="mt-3 text-3xl font-extrabold leading-[1.12] tracking-tight sm:text-[2.6rem]">
            Built for work that cannot lose a week
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted">
            Anywhere the truth is spread across tools and the cost of noticing late is high.
          </p>

          <ul className="mt-8 space-y-1">
            {USE_CASES.map((useCase, index) => (
              <li key={useCase.title}>
                <button
                  type="button"
                  onClick={() => setActive(index)}
                  aria-current={index === active}
                  className={`w-full border-l-2 py-3.5 pl-5 text-left transition-colors duration-150 ${
                    index === active
                      ? 'border-brand'
                      : 'border-line hover:border-line-strong'
                  }`}
                >
                  <span
                    className={`block text-base font-bold tracking-tight ${
                      index === active ? 'text-ink' : 'text-muted'
                    }`}
                  >
                    {useCase.title}
                  </span>
                  {index === active && (
                    <span className="mt-1 block text-sm leading-relaxed text-muted">
                      {useCase.body}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-6 shadow-float sm:p-8">
          <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-faint">
            What the agent cross-references
          </p>
          <h3 className="mt-2 text-lg font-bold tracking-tight">{current.title}</h3>

          <ul className="mt-6 space-y-3">
            {current.signals.map((signal) => (
              <li
                key={signal.looks_for}
                className="flex items-start gap-3 rounded-xl border border-line bg-raised p-4"
              >
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-ink ring-1 ring-inset ring-line">
                  <SourceIcon source={signal.source} className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[11px] font-bold uppercase tracking-[0.08em] text-faint">
                    {SOURCE_LABELS[signal.source]}
                  </span>
                  <span className="mt-0.5 block text-sm font-semibold leading-snug">
                    {signal.looks_for}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  )
}
