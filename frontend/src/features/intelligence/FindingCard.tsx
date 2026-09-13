import { useState } from 'react'

import { Card } from '../../components/ui/Card'
import { SeverityBadge } from '../../components/ui/Badge'
import type { Finding } from './types'

export function FindingCard({ finding }: { finding: Finding }) {
  const [showEvidence, setShowEvidence] = useState(false)

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <h3 className="font-medium">{finding.title}</h3>
          </div>
          <p className="mt-2 text-sm text-slate-600">{finding.description}</p>
        </div>
        <div className="shrink-0 text-sm text-slate-500">
          {Math.round(finding.confidence * 100)}% confident
        </div>
      </div>

      <button
        onClick={() => setShowEvidence(!showEvidence)}
        className="mt-3 text-sm font-medium text-slate-700 underline"
      >
        {showEvidence ? 'Hide evidence' : `Why? (${finding.evidence.length} sources)`}
      </button>

      {showEvidence && (
        <ul className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          {finding.evidence.map((item, index) => (
            <li key={index} className="text-sm">
              <span className="font-medium uppercase text-slate-500">{item.source}</span>
              {' · '}
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="underline">
                  {item.title}
                </a>
              ) : (
                item.title
              )}
              <p className="text-slate-600">{item.content}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
