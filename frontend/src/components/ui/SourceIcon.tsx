import type { Source } from '../../features/intelligence/types'

/* Simplified monochrome marks. One drawing style for all six apps reads as a product
   that integrates them, rather than a page of pasted logos. */

const GLYPHS: Record<Source, React.ReactNode> = {
  slack: (
    <g fill="currentColor">
      <rect x="8.4" y="2.2" width="3.2" height="10.4" rx="1.6" />
      <rect x="12.4" y="11.4" width="3.2" height="10.4" rx="1.6" />
      <rect x="11.4" y="8.4" width="10.4" height="3.2" rx="1.6" />
      <rect x="2.2" y="12.4" width="10.4" height="3.2" rx="1.6" />
    </g>
  ),
  github: (
    <path
      fill="currentColor"
      d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.2 4 18.2 4.3 18.2 4.3c.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3Z"
    />
  ),
  linear: (
    <g fill="none">
      <rect x="2.8" y="2.8" width="18.4" height="18.4" rx="4.8" fill="currentColor" opacity="0.16" />
      <path
        d="M5.6 13.2 10.8 18.4M7.6 7 17 16.4"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </g>
  ),
  gmail: (
    <g stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" fill="none">
      <rect x="2.5" y="4.5" width="19" height="15" rx="2.5" />
      <path d="m3.2 7 8.8 6.6L20.8 7" />
    </g>
  ),
  drive: (
    <g fill="currentColor">
      <path d="M12 2.8 12 13.7 2.6 19.2Z" opacity="0.45" />
      <path d="M12 2.8 21.4 19.2 12 13.7Z" opacity="0.75" />
      <path d="M2.6 19.2 12 13.7l9.4 5.5Z" />
    </g>
  ),
  calendar: (
    <g stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" fill="none">
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M3 10h18M8 3v4M16 3v4" />
      <circle cx="8.5" cy="14.8" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="14.8" r="1.1" fill="currentColor" stroke="none" />
    </g>
  ),
}

export const SOURCE_LABELS: Record<Source, string> = {
  slack: 'Slack',
  gmail: 'Gmail',
  drive: 'Google Drive',
  linear: 'Linear',
  github: 'GitHub',
  calendar: 'Google Calendar',
}

export function SourceIcon({ source, className = 'h-4 w-4' }: { source: Source; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} role="img" aria-label={SOURCE_LABELS[source]}>
      {GLYPHS[source]}
    </svg>
  )
}

/** The icon in its tile — how a source is shown anywhere it heads a block. */
export function SourceAvatar({ source, className = '' }: { source: Source; className?: string }) {
  return (
    <span
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-raised text-ink ring-1 ring-inset ring-line ${className}`}
    >
      <SourceIcon source={source} className="h-[18px] w-[18px]" />
    </span>
  )
}
