import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { useAuth } from '../../lib/auth'

export function FinalCta() {
  const { session } = useAuth()

  return (
    <section className="hero-sky border-t border-line px-6 py-24 text-center">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-extrabold leading-[1.12] tracking-tight sm:text-5xl">
          Stop guessing where the project actually is
        </h2>
        <p className="mt-5 text-base leading-relaxed text-muted sm:text-lg">
          Connect an app, name a project, and run one investigation. The first finding will
          arrive with its evidence attached.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link to={session ? '/app' : '/login'}>
            <Button variant="contrast" size="lg">
              {session ? 'Go to dashboard' : 'Start investigating'}
            </Button>
          </Link>
          <a href="#how">
            <Button variant="secondary" size="lg">
              See how it works
            </Button>
          </a>
        </div>
      </div>
    </section>
  )
}
