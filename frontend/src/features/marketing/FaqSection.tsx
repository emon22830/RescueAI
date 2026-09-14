import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { Section } from './Section'

const FAQS = [
  {
    q: 'Can it change things in my tools without asking?',
    a: 'No. Collection is read-only, and every proposed step sits as pending until you tick it and press approve. That approval is the only path to a write, and each step reports back exactly what the app said.',
  },
  {
    q: 'What happens to an app I have not connected?',
    a: 'It contributes nothing and says so in the run log. The agent never invents a finding to cover a gap — you will see "drive skipped" rather than a guess.',
  },
  {
    q: 'Where do my credentials live?',
    a: 'Slack, Linear, Jira, Asana, Trello, GitHub and Notion tokens are verified against the real API, then stored encrypted against that one project. Google apps currently use one OAuth client configured on the server.',
  },
  {
    q: 'How does it know which project a message is about?',
    a: 'By the name you give the project. The agent matches it against channel names, issue titles, document names and calendar events, and bounds every search to a recent window.',
  },
  {
    q: 'Can it find nothing?',
    a: 'Yes, and that is by design. A model that must find a problem will invent one, so every prompt allows an empty answer. No evidence means no findings; no findings means no plan.',
  },
  {
    q: 'Does it remember old conclusions?',
    a: 'Only as history. Findings and the plan always come from the latest completed run, so a re-sync replaces what is on screen rather than piling onto it.',
  },
]

export function FaqSection() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <Section id="faq">
      <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div>
          <h2 className="text-3xl font-extrabold leading-[1.12] tracking-tight sm:text-[2.6rem]">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted">
            The honest answers — including what the system deliberately will not do.
          </p>

          <div className="mt-8 rounded-2xl border border-line bg-surface p-6 shadow-card">
            <p className="text-sm font-bold tracking-tight">Still deciding?</p>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Connect one app to a project and run a single investigation. If there is nothing
              worth raising, the agent will say so.
            </p>
            <Link to="/login" className="mt-5 inline-block">
              <Button variant="primary" size="md">
                Start investigating
              </Button>
            </Link>
          </div>
        </div>

        <ul className="divide-y divide-line border-y border-line">
          {FAQS.map((faq, index) => (
            <li key={faq.q}>
              <button
                type="button"
                onClick={() => setOpen(open === index ? null : index)}
                aria-expanded={open === index}
                className="flex w-full items-center gap-4 py-5 text-left"
              >
                <span className="text-base font-bold tracking-tight">{faq.q}</span>
                <span className="ml-auto shrink-0 text-faint">
                  {open === index ? (
                    <Icon.Minus className="h-5 w-5" />
                  ) : (
                    <Icon.Plus className="h-5 w-5" />
                  )}
                </span>
              </button>
              {open === index && (
                <p className="-mt-1 pb-5 pr-9 text-sm leading-relaxed text-muted">{faq.a}</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Section>
  )
}
