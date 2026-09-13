import type { Severity } from '../../features/intelligence/types'
import type { ProjectSummary } from '../../features/projects/types'

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-slate-100 text-slate-700',
}

const HEALTH_STYLES: Record<ProjectSummary['health'], { label: string; className: string }> = {
  at_risk: { label: 'At risk', className: 'bg-red-100 text-red-800' },
  watch: { label: 'Watch', className: 'bg-amber-100 text-amber-800' },
  on_track: { label: 'On track', className: 'bg-emerald-100 text-emerald-800' },
}

function Pill({ className, children }: { className: string; children: string }) {
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>{children}</span>
  )
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Pill className={SEVERITY_STYLES[severity]}>{severity.toUpperCase()}</Pill>
}

export function HealthBadge({ health }: { health: ProjectSummary['health'] }) {
  const { label, className } = HEALTH_STYLES[health]
  return <Pill className={className}>{label}</Pill>
}
