import { useState, type FormEvent } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { api, errorMessage } from '../../lib/api'
import type { Source } from '../intelligence/types'
import type { ConnectIntegrationBody, IntegrationStatus } from './types'

const INPUT =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 font-mono text-xs text-ink placeholder:text-faint transition-colors duration-150 focus:border-brand'

/** What each token app asks for beyond the credential itself. */
const CREDENTIAL_LABEL: Record<string, string> = {
  slack: 'Bot token (xoxb-…)',
  linear: 'Personal API key',
  github: 'Fine-grained access token',
}

export function ConnectTokenForm({
  projectId,
  provider,
  setupUrl,
  onConnected,
}: {
  projectId: string
  provider: Source
  setupUrl: string
  onConnected: (status: IntegrationStatus) => void
}) {
  const [token, setToken] = useState('')
  const [repo, setRepo] = useState('')
  const [channelIds, setChannelIds] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const body: ConnectIntegrationBody = { token: token.trim() }
    if (provider === 'github') body.repo = repo.trim()
    if (provider === 'slack' && channelIds.trim()) body.channel_ids = channelIds.trim()

    try {
      // The backend calls the real API with this token before storing it, so a failure
      // here is the app's own words about why it will not work.
      onConnected(await api.connectIntegration(projectId, provider, body))
      setToken('')
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-line bg-raised p-4">
      <label className="block">
        <span className="mb-1.5 block text-xs font-semibold text-muted">
          {CREDENTIAL_LABEL[provider] ?? 'Token'}
        </span>
        <input
          value={token}
          onChange={(event) => setToken(event.target.value)}
          type="password"
          autoComplete="off"
          required
          placeholder="Paste the credential"
          className={INPUT}
        />
      </label>

      {provider === 'github' && (
        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-muted">
            Repository <span className="font-normal text-faint">— owner/name, or a URL</span>
          </span>
          <input
            value={repo}
            onChange={(event) => setRepo(event.target.value)}
            required
            placeholder="owner/name"
            className={INPUT}
          />
        </label>
      )}

      {provider === 'slack' && (
        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold text-muted">
            Channel IDs <span className="font-normal text-faint">— optional</span>
          </span>
          <input
            value={channelIds}
            onChange={(event) => setChannelIds(event.target.value)}
            placeholder="C01ABC,C02DEF — leave blank to read every invited channel"
            className={INPUT}
          />
        </label>
      )}

      {error && <Alert>{error}</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" size="sm" loading={saving}>
          {saving ? 'Verifying…' : 'Connect'}
        </Button>
        <a
          href={setupUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand transition-colors duration-150 hover:text-brand-hover"
        >
          Get the credential
          <Icon.External className="h-3.5 w-3.5" />
        </a>
      </div>
    </form>
  )
}
