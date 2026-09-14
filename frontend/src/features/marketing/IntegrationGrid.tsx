import { Badge } from '../../components/ui/Badge'
import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import { PROVIDERS, SOURCE_ORDER } from '../integrations/providers'
import type { Source } from '../intelligence/types'
import { Section, SectionIntro } from './Section'

/** The apps an approved step can actually be executed against. Drive is the one that
 *  only ever collects. Mirrors executor.WRITE_TARGETS. */
const WRITES: Source[] = [
  'slack',
  'gmail',
  'github',
  'linear',
  'jira',
  'asana',
  'trello',
  'notion',
  'calendar',
]

export function IntegrationGrid() {
  return (
    <Section id="integrations" className="hero-sky border-y border-line">
      <SectionIntro
        eyebrow="Integrations"
        title="Connect the tools your team already uses"
      >
        Every app is read-only by default. Nine of them can also carry out an approved step —
        and only a step you ticked yourself.
      </SectionIntro>

      <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SOURCE_ORDER.map((app) => (
          <div
            key={app}
            className="flex h-full flex-col rounded-2xl border border-line bg-surface p-6 shadow-card transition-colors duration-150 hover:border-line-strong"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-raised text-ink ring-1 ring-inset ring-line">
                <SourceIcon source={app} className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h3 className="truncate font-bold tracking-tight">{SOURCE_LABELS[app]}</h3>
                <p className="truncate text-xs text-muted">{PROVIDERS[app].investigates}</p>
              </div>
            </div>

            <p className="mt-4 text-sm leading-relaxed text-muted">{PROVIDERS[app].collects}</p>

            <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
              <Badge>{PROVIDERS[app].agent} agent</Badge>
              <Badge tone={WRITES.includes(app) ? 'brand' : 'neutral'}>
                {WRITES.includes(app) ? 'Can execute steps' : 'Read-only'}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}
