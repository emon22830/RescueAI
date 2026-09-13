import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import type { Source } from '../intelligence/types'
import { SOURCE_ORDER } from './providers'

/**
 * All six apps at a glance: solid where this project can reach it, faded where it
 * cannot. A faded icon is the honest signal that the agent will skip that app.
 */
export function ConnectorStrip({ connected }: { connected: Source[] }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex items-center gap-1">
        {SOURCE_ORDER.map((source) => {
          const on = connected.includes(source)
          return (
            <span
              key={source}
              title={`${SOURCE_LABELS[source]} — ${on ? 'connected' : 'not connected'}`}
              className={`flex h-6 w-6 items-center justify-center rounded-md ring-1 ring-inset transition-colors duration-150 ${
                on ? 'bg-raised text-ink ring-line' : 'text-faint opacity-45 ring-transparent'
              }`}
            >
              <SourceIcon source={source} className="h-3.5 w-3.5" />
            </span>
          )
        })}
      </span>
      <span className="text-xs text-faint">
        {connected.length}/{SOURCE_ORDER.length} connected
      </span>
    </div>
  )
}
