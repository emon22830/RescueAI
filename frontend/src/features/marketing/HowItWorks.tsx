import { Icon } from '../../components/ui/Icon'
import { Section, SectionIntro } from './Section'

const STEPS = [
  {
    icon: Icon.Search,
    title: 'Collect the evidence',
    body: 'Four investigator agents read your connected apps in parallel and normalize everything they find into one shape — what people said, what was built, what the plan says, what was agreed.',
  },
  {
    icon: Icon.Layers,
    title: 'Cross-reference it',
    body: 'The risk agent compares apps against each other and against time — a requirement that changed after work started is a finding, not a note.',
  },
  {
    icon: Icon.Activity,
    title: 'Draft the recovery plan',
    body: 'Each finding gets concrete steps: move the issue, email the stakeholder, book the alignment meeting.',
  },
  {
    icon: Icon.Shield,
    title: 'You approve, then it acts',
    body: 'Nothing reaches your Slack, your tracker or your calendar until you tick it. Every step reports back what the app actually said.',
  },
]

export function HowItWorks() {
  return (
    <Section id="how">
      <SectionIntro eyebrow="How it works" title="One loop, running on real evidence">
        The agent rebuilds your project&apos;s state from scratch every time you sync. It never
        remembers a conclusion it can no longer prove.
      </SectionIntro>

      <ol className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step, index) => (
          <li
            key={step.title}
            className="relative rounded-2xl border border-line bg-surface p-6 shadow-card"
          >
            <div className="flex items-center justify-between">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-soft text-brand-soft-ink">
                <step.icon className="h-[18px] w-[18px]" />
              </span>
              <span className="text-2xl font-extrabold tabular-nums text-line-strong">
                {index + 1}
              </span>
            </div>
            <h3 className="mt-5 text-base font-bold tracking-tight">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}
