import { Link } from 'react-router-dom'

import { Wordmark } from './Wordmark'

const COLUMNS = [
  {
    heading: 'Product',
    links: [
      { href: '#how', label: 'How it works' },
      { href: '#features', label: 'Features' },
      { href: '#use-cases', label: 'Use cases' },
      { href: '#integrations', label: 'Integrations' },
    ],
  },
  {
    heading: 'Understand it',
    links: [
      { href: '#faq', label: 'FAQ' },
      { href: '#problem', label: 'The problem' },
    ],
  },
]

export function MarketingFooter() {
  return (
    <footer className="border-t border-line bg-surface px-6 py-16">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 md:grid-cols-[minmax(0,1.6fr)_repeat(2,minmax(0,1fr))]">
          <div>
            <Wordmark size="lg" />
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-muted">
              An agent that reconstructs the real state of a project from the tools your team
              already uses, names the blockers with the evidence attached, and acts only with
              your approval.
            </p>
          </div>

          {COLUMNS.map((column) => (
            <nav key={column.heading}>
              <h3 className="text-base font-bold tracking-tight">{column.heading}</h3>
              <ul className="mt-5 space-y-3">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      className="text-sm text-muted transition-colors duration-150 hover:text-ink"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-8">
          <p className="text-xs text-faint">
            Evidence is collected read-only. Nothing is written to a connected app until you
            approve it.
          </p>
          <Link
            to="/login"
            className="text-xs font-semibold text-brand transition-colors duration-150 hover:text-brand-hover"
          >
            Sign in →
          </Link>
        </div>
      </div>
    </footer>
  )
}
