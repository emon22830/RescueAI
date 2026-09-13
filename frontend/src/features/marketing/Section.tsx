import type { ReactNode } from 'react'

/** One band of the landing page. Every section is this wide and this spaced. */
export function Section({
  id,
  children,
  className = '',
}: {
  id?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section id={id} className={`px-6 py-20 sm:py-24 ${className}`}>
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  )
}

/** The centred eyebrow + headline + lede the template uses above most sections. */
export function SectionIntro({
  eyebrow,
  title,
  children,
  align = 'center',
}: {
  eyebrow?: string
  title: string
  children?: ReactNode
  align?: 'center' | 'left'
}) {
  const centred = align === 'center'
  return (
    <div className={centred ? 'mx-auto max-w-2xl text-center' : 'max-w-xl'}>
      {eyebrow && (
        <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-brand">
          {eyebrow}
        </span>
      )}
      <h2
        className={`text-3xl font-extrabold leading-[1.12] tracking-tight sm:text-[2.6rem] ${
          eyebrow ? 'mt-3' : ''
        }`}
      >
        {title}
      </h2>
      {children && <p className="mt-4 text-base leading-relaxed text-muted">{children}</p>}
    </div>
  )
}
