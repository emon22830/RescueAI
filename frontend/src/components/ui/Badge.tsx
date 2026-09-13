import type { ActionStatus, Severity } from '../../features/intelligence/types'
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

const ACTION_STATUS_STYLES: Record<ActionStatus, string> = {
  pending: 'bg-slate-100 text-slate-700',
  approved: 'bg-blue-100 text-blue-800',
  executing: 'bg-amber-100 text-amber-800',
  completed: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
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

export function ActionStatusBadge({ status }: { status: ActionStatus }) {
  return <Pill className={ACTION_STATUS_STYLES[status]}>{status.toUpperCase()}</Pill>
}
