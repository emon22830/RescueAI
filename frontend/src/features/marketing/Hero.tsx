import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { SOURCE_LABELS, SourceIcon } from '../../components/ui/SourceIcon'
import type { Source } from '../intelligence/types'
import { useAuth } from '../../lib/auth'
import { DashboardPreview } from './DashboardPreview'

const APPS: Source[] = ['slack', 'gmail', 'drive', 'linear', 'github', 'calendar']

export function Hero() {
  const { session } = useAuth()

  return (
    <section className="px-6 pb-28 pt-16 sm:pt-20">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/80 px-3.5 py-1.5 text-xs font-semibold text-muted shadow-card backdrop-blur">
            <span className="flex -space-x-1.5">
              {APPS.slice(0, 3).map((app) => (
                <span
                  key={app}
                  className="flex h-5 w-5 items-center justify-center rounded-full border border-line bg-surface text-ink"
                >
                  <SourceIcon source={app} className="h-3 w-3" />
                </span>
              ))}
            </span>
            Six apps, one honest project state
          </span>

          <h1 className="mt-6 text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
            Find Out What Is Actually Blocking Your Project
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
            RescueAI reads Slack, Gmail, Drive, Linear, GitHub and Calendar at the same
            time, names the blocker with the evidence attached, and drafts a recovery plan —
            which it executes only after you approve it.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link to={session ? '/app' : '/login'}>
              <Button variant="primary" size="lg">
                {session ? 'Go to dashboard' : 'Start investigating'}
              </Button>
            </Link>
            <a href="#how">
              <Button variant="ghost" size="lg" icon={<Icon.Play className="h-4 w-4" />}>
                See how it works
              </Button>
            </a>
          </div>
        </div>

        <div className="mx-auto mt-16 max-w-4xl">
          <DashboardPreview />
        </div>

        <div className="mt-16 flex flex-wrap items-center justify-center gap-x-8 gap-y-4">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-faint">
            Investigates
          </span>
          {APPS.map((app) => (
            <span key={app} className="flex items-center gap-2 text-sm font-semibold text-muted">
              <SourceIcon source={app} className="h-4 w-4" />
              {SOURCE_LABELS[app]}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
