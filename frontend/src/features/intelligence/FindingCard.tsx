import { useState } from 'react'

import { SeverityBadge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { Icon } from '../../components/ui/Icon'
import { SourceIcon } from '../../components/ui/SourceIcon'
import { plural } from '../../lib/format'
import { EvidenceItem } from './EvidenceItem'
import type { Finding } from './types'

export function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false)
  const sources = [...new Set(finding.evidence.map((item) => item.source))]

  return (
    <Card>
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={finding.severity} />
              <h3 className="font-semibold tracking-tight">{finding.title}</h3>
            </div>
            <p className="mt-2.5 text-sm leading-relaxed text-muted">{finding.description}</p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-lg font-semibold tabular-nums">
              {Math.round(finding.confidence * 100)}%
            </div>
            <div className="text-xs text-faint">confidence</div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-ink transition-colors duration-150 hover:bg-raised"
        >
          <span className="flex items-center gap-1 text-faint">
            {sources.map((source) => (
              <SourceIcon key={source} source={source} className="h-3.5 w-3.5" />
            ))}
          </span>
          {open ? 'Hide evidence' : `Why? ${plural(finding.evidence.length, 'source')}`}
          <Icon.Chevron className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {open && (
        <div className="border-t border-line bg-surface p-5 pt-4">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
            The evidence this finding cites
          </p>
          <ul className="space-y-2.5">
            {finding.evidence.map((item, index) => (
              <EvidenceItem key={`${item.source}-${index}`} evidence={item} />
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}
