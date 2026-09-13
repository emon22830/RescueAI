import { SourceIcon } from '../../components/ui/SourceIcon'
import { Icon } from '../../components/ui/Icon'
import type { Source } from '../intelligence/types'

/* Small static illustrations for the three feature cards. Each one shows the real shape
   of a screen in the product, filled with the example scenario. */

function Row({ source, title, meta }: { source: Source; title: string; meta: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-line bg-surface px-3 py-2.5">
      <SourceIcon source={source} className="h-3.5 w-3.5 shrink-0 text-muted" />
      <span className="truncate text-xs font-semibold">{title}</span>
      <span className="ml-auto shrink-0 text-[11px] text-faint">{meta}</span>
    </div>
  )
}

export function EvidenceVisual() {
  return (
    <div className="space-y-2">
      <Row source="slack" title="#saas-product-launch" meta="4 days ago" />
      <Row source="gmail" title="Re: v3 is final" meta="3 weeks ago" />
      <Row source="github" title="#482 Payment capture" meta="draft" />
      <Row source="calendar" title="Launch review" meta="in 6 days" />
    </div>
  )
}

export function FindingVisual() {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-danger px-2 py-0.5 text-[10px] font-bold text-white">
          CRITICAL
        </span>
        <span className="ml-auto text-xs font-bold tabular-nums">93%</span>
      </div>
      <p className="mt-2.5 text-xs font-bold leading-snug">
        Payment API is blocked by a requirements change
      </p>
      <div className="mt-3 flex items-center gap-1.5 border-t border-line pt-3">
        <SourceIcon source="slack" className="h-3.5 w-3.5 text-faint" />
        <SourceIcon source="gmail" className="h-3.5 w-3.5 text-faint" />
        <SourceIcon source="linear" className="h-3.5 w-3.5 text-faint" />
        <span className="text-[11px] font-semibold text-brand">Why? 3 sources</span>
      </div>
    </div>
  )
}

export function ApprovalVisual() {
  const steps = [
    { label: 'Move PAY-124 to Blocked', app: 'linear' as Source, checked: true },
    { label: 'Email the PM for the live spec', app: 'gmail' as Source, checked: true },
    { label: 'Book a spec alignment', app: 'calendar' as Source, checked: false },
  ]
  return (
    <div className="space-y-2">
      {steps.map((step) => (
        <div
          key={step.label}
          className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 ${
            step.checked ? 'border-brand/40 bg-brand-soft/50' : 'border-line bg-surface'
          }`}
        >
          <span
            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded ${
              step.checked ? 'bg-brand text-brand-ink' : 'border border-line-strong'
            }`}
          >
            {step.checked && <Icon.Check className="h-3 w-3" />}
          </span>
          <SourceIcon source={step.app} className="h-3.5 w-3.5 shrink-0 text-muted" />
          <span className="truncate text-xs font-semibold">{step.label}</span>
        </div>
      ))}
      <div className="flex h-9 items-center justify-center rounded-lg bg-brand text-xs font-bold text-brand-ink">
        Approve &amp; execute 2 actions
      </div>
    </div>
  )
}
