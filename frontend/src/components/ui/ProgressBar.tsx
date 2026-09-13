/**
 * Progress as the agent measured it. `null` means the evidence did not support a
 * number — it renders as "Not measured", never as 0%.
 */
export function ProgressBar({ value, label = 'Progress' }: { value: number | null; label?: string }) {
  if (value === null) {
    return (
      <div>
        <div className="flex items-baseline justify-between text-xs">
          <span className="text-faint">{label}</span>
          <span className="text-faint">Not measured</span>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-raised ring-1 ring-inset ring-line" />
      </div>
    )
  }

  const clamped = Math.min(100, Math.max(0, value))
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-faint">{label}</span>
        <span className="font-medium tabular-nums text-ink">{clamped}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-raised ring-1 ring-inset ring-line">
        <div
          className="h-full rounded-full bg-brand transition-[width] duration-200"
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
        />
      </div>
    </div>
  )
}
