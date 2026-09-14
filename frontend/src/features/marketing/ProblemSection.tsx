import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import type { Source } from '../intelligence/types'
import { Section } from './Section'

const VOICES: { source: Source; says: string; when: string }[] = [
  { source: 'linear', says: '“Payment capture — In Progress”', when: 'Unchanged for 19 days' },
  { source: 'slack', says: '“We’re blocked until someone confirms the spec”', when: 'Asked three times' },
  { source: 'drive', says: '“Requirements v3 — tokenized charges”', when: 'Replaced v2 on 26 Aug' },
]

export function ProblemSection() {
  return (
    <Section className="border-y border-line bg-surface">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-2xl font-extrabold leading-tight tracking-tight sm:text-[2rem]">
          Nobody is lying. Nobody is looking at every place at once.
        </h2>
        <p className="mt-4 text-base leading-relaxed text-muted">
          A project&apos;s real state is never in one tool. Each app is telling the truth about
          its own corner, and the contradiction between them is the thing that costs you the
          week.
        </p>
      </div>

      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {VOICES.map((voice) => (
          <div key={voice.source} className="rounded-2xl border border-line bg-raised p-6">
            <div className="flex items-center gap-2.5">
              <SourceIcon source={voice.source} className="h-4 w-4 text-muted" />
              <span className="text-xs font-bold uppercase tracking-[0.1em] text-faint">
                {SOURCE_LABELS[voice.source]}
              </span>
            </div>
            <p className="mt-4 min-h-[3rem] text-[15px] font-semibold leading-snug">{voice.says}</p>
            <p className="mt-2 text-sm text-muted">{voice.when}</p>
          </div>
        ))}
      </div>

      <p className="mx-auto mt-10 max-w-3xl rounded-2xl border border-brand/25 bg-brand-soft px-6 py-5 text-center text-[15px] font-semibold leading-relaxed text-brand-soft-ink">
        The sentence no single app can produce: the payment API is blocked because the
        requirements changed after implementation started — and the launch review is in six days.
      </p>
    </Section>
  )
}
