import type { ReactNode } from 'react'

/**
 * `backend/.env` is unset most of the time, so empty is the first state most people
 * see. It explains what will appear here and how to get it — it never apologises and
 * it never stands in for data.
 */
export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode
  title: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      {icon && (
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-raised text-faint ring-1 ring-inset ring-line">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{children}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
