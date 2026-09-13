export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={`animate-rescue-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** A block in the shape of the thing still loading. Never a bare "Loading…". */
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-rescue-pulse rounded-lg bg-raised ${className}`} />
}

/** The loading state for a list of cards. */
export function SkeletonCards({ count = 3, height = 'h-28' }: { count?: number; height?: string }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} className={`w-full border border-line ${height}`} />
      ))}
    </div>
  )
}
