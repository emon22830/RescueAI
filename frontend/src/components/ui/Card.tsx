import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  /** Adds a hover lift. Only for a card that is itself a link. */
  interactive?: boolean
}

export function Card({ children, className = '', interactive = false }: CardProps) {
  const hover = interactive
    ? 'transition-colors duration-150 hover:border-line-strong hover:bg-raised'
    : ''
  return (
    <div className={`rounded-xl border border-line bg-surface ${hover} ${className}`}>
      {children}
    </div>
  )
}

/** A titled panel: the shape almost every block on a page takes. */
export function Panel({
  title,
  caption,
  action,
  children,
  bodyClassName = 'p-5',
}: {
  title: string
  caption?: string
  action?: ReactNode
  children: ReactNode
  bodyClassName?: string
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
        <div>
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          {caption && <p className="mt-0.5 text-xs text-faint">{caption}</p>}
        </div>
        {action}
      </div>
      <div className={bodyClassName}>{children}</div>
    </Card>
  )
}

/** A heading for a run of cards that are not wrapped in a Panel. */
export function SectionHeading({
  title,
  caption,
  action,
}: {
  title: string
  caption?: string
  action?: ReactNode
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {caption && <p className="mt-0.5 text-xs text-faint">{caption}</p>}
      </div>
      {action}
    </div>
  )
}
