import type { ReactNode } from 'react'

type Tone = 'danger' | 'warn' | 'info'

const TONES: Record<Tone, string> = {
  danger: 'border-danger/30 bg-danger-soft text-danger',
  warn: 'border-warn/30 bg-warn-soft text-warn',
  info: 'border-brand/25 bg-brand-soft text-brand-soft-ink',
}

/** Shows what the API actually said. Never a friendly rewrite of a real error. */
export function Alert({
  tone = 'danger',
  title,
  children,
  action,
}: {
  tone?: Tone
  title?: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : undefined}
      className={`flex flex-wrap items-start justify-between gap-4 rounded-xl border px-4 py-3 text-sm ${TONES[tone]}`}
    >
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <p className={`break-words ${title ? 'mt-0.5 opacity-90' : ''}`}>{children}</p>
      </div>
      {action}
    </div>
  )
}
