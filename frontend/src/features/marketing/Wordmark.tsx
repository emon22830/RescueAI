/** The product mark. Shared by the marketing header, the footer and the app shell. */
export function Wordmark({ size = 'md' }: { size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'h-10 w-10' : 'h-8 w-8'
  const glyph = size === 'lg' ? 'h-[22px] w-[22px]' : 'h-[18px] w-[18px]'
  const text = size === 'lg' ? 'text-xl' : 'text-[0.95rem]'

  return (
    <span className="flex shrink-0 items-center gap-2.5">
      <span
        className={`flex ${box} shrink-0 items-center justify-center rounded-xl bg-brand text-brand-ink`}
      >
        <svg viewBox="0 0 24 24" className={glyph} fill="none" aria-hidden>
          <circle cx="12" cy="12" r="7.5" stroke="currentColor" strokeWidth="1.8" opacity="0.5" />
          <circle cx="12" cy="12" r="2.6" fill="currentColor" />
          <path
            d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <span className={`font-extrabold tracking-tight ${text}`}>RescueAI</span>
    </span>
  )
}
