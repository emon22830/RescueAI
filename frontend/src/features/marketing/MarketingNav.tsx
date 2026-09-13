import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { ThemeToggle } from '../../components/layout/ThemeToggle'
import { useAuth } from '../../lib/auth'
import { Wordmark } from './Wordmark'

const LINKS = [
  { href: '#how', label: 'How it works' },
  { href: '#features', label: 'Features' },
  { href: '#use-cases', label: 'Use cases' },
  { href: '#integrations', label: 'Integrations' },
  { href: '#faq', label: 'FAQ' },
]

/** The floating bar: inset from the page edges so the hero sky runs around it, and
 *  fully opaque — a translucent surface here lets the wash tint the bar, which is what
 *  makes the logo sit on a colour that shifts as the page scrolls under it. */
export function MarketingNav() {
  const { session } = useAuth()
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="mx-auto max-w-6xl rounded-2xl border border-line bg-surface shadow-float">
        <div className="flex h-16 items-center gap-6 px-4 sm:px-6">
          <Link to="/" aria-label="RescueAI home" className="shrink-0">
            <Wordmark />
          </Link>

          {/* flex-1 between two shrink-0 ends, so the links centre in the bar rather
              than trailing the wordmark. */}
          <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
            {LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors duration-150 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-2 lg:ml-0">
            <ThemeToggle />
            {session ? (
              <Link to="/app">
                <Button variant="contrast" size="md">
                  Go to dashboard
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login" className="hidden sm:block">
                  <Button variant="secondary" size="md">
                    Sign in
                  </Button>
                </Link>
                <Link to="/login">
                  <Button variant="contrast" size="md">
                    Get started
                  </Button>
                </Link>
              </>
            )}
            <button
              type="button"
              onClick={() => setOpen(!open)}
              aria-label={open ? 'Close menu' : 'Open menu'}
              aria-expanded={open}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-raised hover:text-ink lg:hidden"
            >
              {open ? <Icon.Close className="h-5 w-5" /> : <Icon.Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {open && (
          <nav className="grid gap-1 border-t border-line px-4 py-3 lg:hidden">
            {LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors duration-150 hover:bg-raised hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
        )}
      </div>
    </header>
  )
}
