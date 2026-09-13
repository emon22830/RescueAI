import { Card } from '../../components/ui/Card'
import { ProgressBar } from '../../components/ui/ProgressBar'
import { StatTile } from '../../components/ui/StatTile'
import type { ProjectSummary } from './types'

/**
 * The sentence no single app could produce, plus the numbers behind it. Both come
 * from the latest completed run — nothing here is recomputed in the browser.
 */
export function ProjectState({
  summary,
  evidenceCount,
}: {
  summary: ProjectSummary
  /** Items collected in the latest run, or null when there is no run to read. */
  evidenceCount: number | null
}) {
  return (
    <div className="grid items-start gap-4 lg:grid-cols-3">
      <Card className="p-5 lg:col-span-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-faint">
          What the agent concluded
        </span>
        <p className="mt-3 text-[15px] leading-relaxed text-ink">
          {summary.summary || 'The last run produced no written state for this project.'}
        </p>
        <div className="mt-6">
          <ProgressBar value={summary.progress} label="Progress toward the goal" />
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-1 lg:grid-rows-2">
        <StatTile
          label="Blockers"
          value={summary.blockers}
          tone={summary.blockers > 0 ? 'danger' : 'neutral'}
          caption="Stopping work right now"
        />
        <StatTile
          label="Risks"
          value={summary.risks}
          tone={summary.risks > 0 ? 'warn' : 'neutral'}
          caption={
            evidenceCount === null
              ? 'Not measured yet'
              : `From ${evidenceCount} pieces of evidence`
          }
        />
      </div>
    </div>
  )
}
