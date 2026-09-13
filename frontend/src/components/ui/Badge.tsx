import type { ReactNode } from 'react'

import type { ActionStatus, Severity } from '../../features/intelligence/types'
import type { Health } from '../../features/projects/types'

type Tone = 'neutral' | 'brand' | 'danger' | 'warn' | 'success' | 'danger-solid'

const TONES: Record<Tone, string> = {
  neutral: 'bg-raised text-faint ring-1 ring-inset ring-line',
  brand: 'bg-brand-soft text-brand-soft-ink',
  danger: 'bg-danger-soft text-danger',
  warn: 'bg-warn-soft text-warn',
  success: 'bg-success-soft text-success',
  'danger-solid': 'bg-danger text-white',
}

export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

/* --- product vocabulary -----------------------------------------------------
   Health and severity are named the same way on every screen. Change a word here
   and it changes everywhere, which is the point. */

const HEALTH: Record<Health, { label: string; tone: Tone }> = {
  on_track: { label: 'On track', tone: 'success' },
  watch: { label: 'Watch', tone: 'warn' },
  at_risk: { label: 'At risk', tone: 'danger' },
}

const SEVERITY: Record<Severity, { label: string; tone: Tone }> = {
  critical: { label: 'Critical', tone: 'danger' },
  high: { label: 'High', tone: 'danger' },
  medium: { label: 'Medium', tone: 'warn' },
  low: { label: 'Low', tone: 'neutral' },
}

const ACTION: Record<ActionStatus, { label: string; tone: Tone }> = {
  pending: { label: 'Awaiting approval', tone: 'neutral' },
  approved: { label: 'Approved', tone: 'brand' },
  executing: { label: 'Executing', tone: 'warn' },
  completed: { label: 'Done', tone: 'success' },
  failed: { label: 'Failed', tone: 'danger' },
}

function Dot({ tone }: { tone: Tone }) {
  const color =
    tone === 'success'
      ? 'bg-success'
      : tone === 'danger' || tone === 'danger-solid'
        ? 'bg-danger'
        : tone === 'warn'
          ? 'bg-warn'
          : tone === 'brand'
            ? 'bg-brand'
            : 'bg-faint'
  return <span className={`h-1.5 w-1.5 rounded-full ${color}`} aria-hidden />
}

export function HealthBadge({ health }: { health: Health }) {
  const { label, tone } = HEALTH[health]
  return (
    <Badge tone={tone}>
      <Dot tone={tone} />
      {label}
    </Badge>
  )
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { label, tone } = SEVERITY[severity]
  // Critical is the one thing on screen loud enough to read from across a room.
  return <Badge tone={severity === 'critical' ? 'danger-solid' : tone}>{label}</Badge>
}

export function ActionStatusBadge({ status }: { status: ActionStatus }) {
  const { label, tone } = ACTION[status]
  return (
    <Badge tone={tone} className={status === 'executing' ? 'animate-rescue-pulse' : ''}>
      {status === 'executing' && <Dot tone={tone} />}
      {label}
    </Badge>
  )
}

export function ConnectionBadge({ connected }: { connected: boolean }) {
  return (
    <Badge tone={connected ? 'success' : 'neutral'}>
      <Dot tone={connected ? 'success' : 'neutral'} />
      {connected ? 'Connected' : 'Not connected'}
    </Badge>
  )
}
