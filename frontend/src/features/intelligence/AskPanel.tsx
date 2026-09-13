import { useEffect, useRef, useState } from 'react'

import { Panel } from '../../components/ui/Card'
import { api, errorMessage } from '../../lib/api'
import type { Project } from '../projects/types'
import { AskAnswer, type Exchange } from './AskAnswer'
import { AskComposer } from './AskComposer'

const SUGGESTIONS = [
  'What is blocking this project right now?',
  'What changed in the last week?',
  'Is anything overdue, and who owns it?',
  'Who should I follow up with today?',
  'Write me a status update for the team',
]

/**
 * Ask a question about one project. The backend answers only from the evidence the
 * latest completed run collected, so this is a view onto the stored state rather than
 * a chatbot — an answer it cannot ground comes back marked as such.
 *
 * The thread lives in component state: it is a way of reading the run, not a record
 * worth keeping, so nothing is persisted.
 */
export function AskPanel({ projects }: { projects: Project[] }) {
  const [projectId, setProjectId] = useState('')
  const [question, setQuestion] = useState('')
  const [thread, setThread] = useState<Exchange[]>([])
  const [sending, setSending] = useState(false)
  const nextId = useRef(0)

  // Projects arrive after the first render; pick one as soon as there is one to pick.
  useEffect(() => {
    setProjectId((current) =>
      projects.some((project) => project.id === current) ? current : (projects[0]?.id ?? ''),
    )
  }, [projects])

  async function send(text: string) {
    const asked = text.trim()
    if (!asked || !projectId || sending) return

    const id = nextId.current++
    setThread((current) => [...current, { id, question: asked, answer: null, error: null }])
    setQuestion('')
    setSending(true)

    try {
      const answer = await api.askProject(projectId, asked)
      setThread((current) =>
        current.map((item) => (item.id === id ? { ...item, answer } : item)),
      )
    } catch (caught) {
      const message = errorMessage(caught)
      setThread((current) =>
        current.map((item) => (item.id === id ? { ...item, error: message } : item)),
      )
    } finally {
      setSending(false)
    }
  }

  const selector =
    projects.length > 1 ? (
      <select
        value={projectId}
        onChange={(event) => setProjectId(event.target.value)}
        aria-label="Project to ask about"
        className="max-w-[14rem] shrink-0 truncate rounded-lg border border-line-strong bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink"
      >
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    ) : undefined

  return (
    <Panel
      title="Ask the agent"
      caption="Ask in your own words. Answers come only from evidence the latest run collected, and cite it"
      action={selector}
      bodyClassName="p-5 space-y-4"
    >
      {thread.length > 0 && (
        <ul className="space-y-6">
          {thread.map((exchange, index) => (
            <AskAnswer
              key={exchange.id}
              exchange={exchange}
              latest={index === thread.length - 1}
              onFollowUp={(text) => void send(text)}
            />
          ))}
        </ul>
      )}

      <AskComposer
        value={question}
        onChange={setQuestion}
        onSubmit={(text) => void send(text)}
        sending={sending}
        ready={Boolean(projectId)}
        suggestions={thread.length === 0 && projectId ? SUGGESTIONS : undefined}
      />
    </Panel>
  )
}
