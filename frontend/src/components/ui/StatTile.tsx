import type { ReactNode } from 'react'

import { Card } from './Card'

type Tone = 'neutral' | 'danger' | 'warn' | 'success'

const VALUE_TONES: Record<Tone, string> = {
  neutral: 'text-ink',
  danger: 'text-danger',
  warn: 'text-warn',
  success: 'text-success',
}

/**
 * One number from the API. `tone` is for a number that is bad news — blockers that
 * exist, actions that failed — and stays neutral when the number is zero.
 */
export function StatTile({
  label,
  value,
  caption,
  tone = 'neutral',
  icon,
}: {
  label: string
  value: ReactNode
  caption?: string
  tone?: Tone
  icon?: ReactNode
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
          {label}
        </span>
        {icon && <span className="text-faint">{icon}</span>}
      </div>
      <div className={`mt-3 text-3xl font-semibold tabular-nums tracking-tight ${VALUE_TONES[tone]}`}>
        {value}
      </div>
      {caption && <p className="mt-1 text-xs text-faint">{caption}</p>}
    </Card>
  )
}
