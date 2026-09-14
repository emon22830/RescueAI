import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import { plural } from '../../lib/format'
import type { Source } from '../intelligence/types'
import { SOURCE_ORDER } from './providers'

/**
 * Which apps this project is actually reading.
 *
 * Only the connected ones. A team runs one tracker, not four, so fading out the eight
 * it will never connect would read as eight things wrong with the project — and at ten
 * apps the row stopped fitting a card on a phone. What is still available to connect is
 * the Connections page's job, where there is room to say it properly.
 */
export function ConnectorStrip({ connected }: { connected: Source[] }) {
  const apps = SOURCE_ORDER.filter((source) => connected.includes(source))

  if (apps.length === 0) {
    return <span className="text-xs text-faint">No apps connected — the agent has nothing to read</span>
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex flex-wrap items-center gap-1">
        {apps.map((source) => (
          <span
            key={source}
            title={`${SOURCE_LABELS[source]} — connected`}
            className="flex h-6 w-6 items-center justify-center rounded-md bg-raised text-ink ring-1 ring-inset ring-line"
          >
            <SourceIcon source={source} className="h-3.5 w-3.5" />
          </span>
        ))}
      </span>
      <span className="text-xs text-faint">{plural(apps.length, 'app')} connected</span>
    </div>
  )
}
