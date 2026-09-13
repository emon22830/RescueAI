import { FaqSection } from '../features/marketing/FaqSection'
import { FeatureSection } from '../features/marketing/FeatureSection'
import { FinalCta } from '../features/marketing/FinalCta'
import { Hero } from '../features/marketing/Hero'
import { HowItWorks } from '../features/marketing/HowItWorks'
import { IntegrationGrid } from '../features/marketing/IntegrationGrid'
import { MarketingFooter } from '../features/marketing/MarketingFooter'
import { MarketingNav } from '../features/marketing/MarketingNav'
import { ProblemSection } from '../features/marketing/ProblemSection'
import { UseCases } from '../features/marketing/UseCases'

/** The public page. Everything below the nav is static — it makes no API call, so it
 *  renders on a machine where the backend is not running at all. */
export function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* The nav floats *over* the sky rather than above it — otherwise the page
          background shows through around the bar and draws a seam across the top. */}
      <div className="hero-sky">
        <MarketingNav />
        <Hero />
      </div>
      <main>
        <div id="problem">
          <ProblemSection />
        </div>
        <HowItWorks />
        <FeatureSection />
        <UseCases />
        <IntegrationGrid />
        <FaqSection />
        <FinalCta />
      </main>
      <MarketingFooter />
    </div>
  )
}
