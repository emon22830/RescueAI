import { useState, type FormEvent } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { api, errorMessage } from '../../lib/api'
import type { Source } from '../intelligence/types'
import { CREDENTIAL_LABEL, EXTRA_FIELDS } from './providers'
import type { ConnectIntegrationBody, IntegrationStatus } from './types'

const INPUT =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 font-mono text-xs text-ink placeholder:text-faint transition-colors duration-150 focus:border-brand'

/** Paste a credential, and whatever else the app needs to be reachable. The backend
 *  calls the real API with it before storing anything, so a failure here is that app's
 *  own words about why it will not work. */
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
  const [extras, setExtras] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fields = EXTRA_FIELDS[provider] ?? []

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const body: ConnectIntegrationBody = { token: token.trim() }
    for (const field of fields) {
      const value = (extras[field.name] ?? '').trim()
      if (value) body[field.name] = value
    }

    try {
      onConnected(await api.connectIntegration(projectId, provider, body))
      setToken('')
      setExtras({})
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

      {fields.map((field) => (
        <label key={field.name} className="block">
          <span className="mb-1.5 block text-xs font-semibold text-muted">
            {field.label}
            {field.hint && <span className="font-normal text-faint"> — {field.hint}</span>}
          </span>
          <input
            value={extras[field.name] ?? ''}
            onChange={(event) =>
              setExtras((current) => ({ ...current, [field.name]: event.target.value }))
            }
            required={field.required}
            placeholder={field.placeholder}
            className={INPUT}
          />
        </label>
      ))}

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
