import { Icon } from '../../components/ui/Icon'
import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import { humanize, timeAgo } from '../../lib/format'
import type { Evidence } from './types'

/**
 * One collected item, shown as the app said it. The link out is what makes a finding
 * checkable — when the API gave a url, it is here.
 */
export function EvidenceItem({ evidence }: { evidence: Evidence }) {
  return (
    <li className="rounded-lg border border-line bg-raised p-3.5">
      <div className="flex items-center gap-2 text-xs text-faint">
        <SourceIcon source={evidence.source} className="h-3.5 w-3.5" />
        <span className="font-medium text-muted">{SOURCE_LABELS[evidence.source]}</span>
        <span aria-hidden>·</span>
        <span>{humanize(evidence.type)}</span>
        <span className="ml-auto shrink-0">{timeAgo(evidence.timestamp)}</span>
      </div>

      <p className="mt-2 text-sm font-medium text-ink">
        {evidence.url ? (
          <a
            href={evidence.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 break-words text-brand transition-colors duration-150 hover:text-brand-hover"
          >
            {evidence.title}
            <Icon.External className="h-3.5 w-3.5 shrink-0" />
          </a>
        ) : (
          evidence.title
        )}
      </p>

      <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-muted">
        {evidence.content}
      </p>
    </li>
  )
}
