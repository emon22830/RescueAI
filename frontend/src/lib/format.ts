/** Display helpers. Nothing here invents a value — a missing one stays missing. */

const UNITS: [limit: number, seconds: number, name: Intl.RelativeTimeFormatUnit][] = [
  [60, 1, 'second'],
  [3600, 60, 'minute'],
  [86400, 3600, 'hour'],
  [604800, 86400, 'day'],
  [2629800, 604800, 'week'],
  [31557600, 2629800, 'month'],
  [Infinity, 31557600, 'year'],
]

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

/** "4 minutes ago". Returns an em dash for a timestamp the API did not send. */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—'
  const elapsed = (Date.now() - new Date(iso).getTime()) / 1000
  if (Number.isNaN(elapsed)) return '—'

  const [, seconds, unit] = UNITS.find(([limit]) => Math.abs(elapsed) < limit)!
  return relative.format(-Math.round(elapsed / seconds), unit)
}

/** "14 Mar, 09:41". Used where the exact moment matters more than the distance. */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** How long a run took, from its two timestamps. */
export function duration(from: string, to: string | null): string {
  if (!to) return '—'
  const seconds = Math.max(0, (new Date(to).getTime() - new Date(from).getTime()) / 1000)
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds / 60)}m`
}

/** Turns `update_due_date` into `Update due date` for a label. */
export function humanize(value: string): string {
  const words = value.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}
