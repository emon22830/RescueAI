import { SourceIcon } from '../../components/ui/SourceIcon'
import type { Source } from '../intelligence/types'

/* An illustration of the product, not a live dashboard — the scenario is labelled as an
   example inside the frame. Real project data only ever renders in the app itself. */

const CITED: { source: Source; label: string }[] = [
  { source: 'slack', label: '#saas-product-launch' },
  { source: 'gmail', label: 'Re: v3 is final' },
  { source: 'linear', label: 'PAY-124' },
]

function WindowChrome() {
  return (
    <div className="flex items-center gap-2 border-b border-line bg-raised px-4 py-3">
      <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
      <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
      <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
      <span className="ml-3 text-[11px] font-medium text-faint">Example project</span>
    </div>
  )
}

export function DashboardPreview() {
  return (
    <div className="relative">
      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-float">
        <WindowChrome />

        <div className="p-5 sm:p-7">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-lg font-bold tracking-tight">SaaS Product Launch</h3>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger-soft px-2.5 py-1 text-xs font-semibold text-danger">
              <span className="h-1.5 w-1.5 rounded-full bg-danger" />
              At risk
            </span>
          </div>

          <p className="mt-4 text-[15px] leading-relaxed text-ink">
            The payment API is blocked because the requirements changed after implementation
            started. It is on the critical path for launch, and the launch review is in six days.
          </p>

          <div className="mt-5">
            <div className="flex items-baseline justify-between text-xs">
              <span className="text-faint">Progress toward the goal</span>
              <span className="font-semibold tabular-nums">40%</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-raised ring-1 ring-inset ring-line">
              <div className="h-full w-[40%] rounded-full bg-brand" />
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-line bg-raised p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-danger px-2.5 py-1 text-xs font-semibold text-white">
                Critical
              </span>
              <span className="text-sm font-semibold">
                Payment API is blocked by a requirements change
              </span>
              <span className="ml-auto text-sm font-bold tabular-nums">93%</span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {CITED.map((item) => (
                <span
                  key={item.label}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-muted"
                >
                  <SourceIcon source={item.source} className="h-3.5 w-3.5" />
                  {item.label}
                </span>
              ))}
            </div>
          </div>

          {/* The step the finding produced — pending, which is the whole point. */}
          <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-brand/30 bg-brand-soft/60 p-4">
            <SourceIcon source="linear" className="h-4 w-4 shrink-0 text-brand-soft-ink" />
            <span className="text-sm font-semibold text-ink">
              Move PAY-124 to Blocked in Linear
            </span>
            <span className="ml-auto shrink-0 rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-muted ring-1 ring-inset ring-line">
              Awaiting your approval
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
