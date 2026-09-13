import type { ReactNode } from 'react'

import { ApprovalVisual, EvidenceVisual, FindingVisual } from './FeatureVisuals'
import { Section, SectionIntro } from './Section'

const FEATURES: { title: string; body: string; visual: ReactNode; tint: string }[] = [
  {
    title: 'Evidence, not summaries',
    body: 'Every app already summarises itself. We collect the raw items — messages, issues, commits, documents, meetings — and normalize them so they can be compared.',
    visual: <EvidenceVisual />,
    tint: 'from-brand-soft to-surface',
  },
  {
    title: 'Findings that cite their sources',
    body: 'A finding always carries the evidence it was drawn from, linked back to the real message or issue. A finding with nothing behind it is a bug, not a feature.',
    visual: <FindingVisual />,
    tint: 'from-danger-soft to-surface',
  },
  {
    title: 'Nothing is written without you',
    body: 'The plan sits as pending until you tick the steps you want. Approval is the only thing in the system that can change someone else’s workspace.',
    visual: <ApprovalVisual />,
    tint: 'from-success-soft to-surface',
  },
]

export function FeatureSection() {
  return (
    <Section id="features" className="border-y border-line bg-surface">
      <SectionIntro eyebrow="Features" title="Everything you need to see the real state">
        Built around one rule: the system never says a project is at risk without showing you
        exactly why.
      </SectionIntro>

      <div className="mt-14 grid gap-5 lg:grid-cols-3">
        {FEATURES.map((feature) => (
          <article
            key={feature.title}
            className="flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-canvas shadow-card"
          >
            <div className={`flex min-h-[15rem] items-center bg-gradient-to-b ${feature.tint} p-5`}>
              {feature.visual}
            </div>
            <div className="flex-1 border-t border-line bg-surface p-6">
              <h3 className="text-lg font-bold tracking-tight">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{feature.body}</p>
            </div>
          </article>
        ))}
      </div>
    </Section>
  )
}
