import { useState } from 'react'

import { Badge, ConnectionBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Icon } from '../../components/ui/Icon'
import { SOURCE_LABELS, SourceAvatar } from '../../components/ui/SourceIcon'
import { api, errorMessage } from '../../lib/api'
import { ConnectTokenForm } from './ConnectTokenForm'
import { PROVIDERS } from './providers'
import type { IntegrationStatus } from './types'

/**
 * One app on one project. A `token` app is connected right here — the credential is
 * verified against the real API and stored encrypted. An `oauth` app sends the user to
 * Google for consent and stores the grant the same way. Either way the credential
 * belongs to this project alone, and no credential value is ever shown back.
 */
export function ConnectionCard({
  projectId,
  status,
  onChanged,
}: {
  projectId: string
  status: IntegrationStatus
  onChanged: (status: IntegrationStatus) => void
}) {
  const copy = PROVIDERS[status.id]
  const [disconnecting, setDisconnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function disconnect() {
    setDisconnecting(true)
    setError(null)
    try {
      await api.disconnectIntegration(projectId, status.id)
      onChanged({ ...status, connected: false, metadata: {} })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setDisconnecting(false)
    }
  }

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3.5">
        <SourceAvatar source={status.id} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-bold tracking-tight">{SOURCE_LABELS[status.id]}</h3>
            <ConnectionBadge connected={status.connected} />
          </div>
          <p className="mt-0.5 text-sm text-muted">{copy.investigates}</p>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-muted">{copy.collects}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge>{copy.agent} agent</Badge>
        <Badge tone={status.writes_back ? 'brand' : 'neutral'}>
          {status.writes_back ? 'Can execute approved actions' : 'Read-only'}
        </Badge>
      </div>

      <div className="mt-5">
        {status.connected ? (
          <ConnectedPanel
            status={status}
            disconnecting={disconnecting}
            onDisconnect={disconnect}
          />
        ) : status.mode === 'token' ? (
          <ConnectTokenForm
            projectId={projectId}
            provider={status.id}
            setupUrl={status.setup_url}
            onConnected={onChanged}
          />
        ) : (
          <ConnectGooglePanel projectId={projectId} status={status} />
        )}
      </div>

      {error && <p className="mt-3 text-xs text-danger">{error}</p>}
    </Card>
  )
}

/** What the app told us about itself when the credential was verified. */
function ConnectedPanel({
  status,
  disconnecting,
  onDisconnect,
}: {
  status: IntegrationStatus
  disconnecting: boolean
  onDisconnect?: () => void
}) {
  // Google records the apps one consent covers as a list; everything else is a string.
  const facts = Object.entries(status.metadata)
    .map(([key, value]) => [key, Array.isArray(value) ? value.join(', ') : value] as const)
    .filter(([, value]) => value)

  return (
    <div className="rounded-xl border border-line bg-raised p-4">
      <div className="flex items-start gap-2">
        <Icon.Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
        <div className="min-w-0 flex-1">
          {facts.length > 0 ? (
            <dl className="space-y-1">
              {facts.map(([key, value]) => (
                <div key={key} className="flex gap-2 text-xs">
                  <dt className="shrink-0 capitalize text-faint">{key.replace(/_/g, ' ')}</dt>
                  <dd className="min-w-0 break-all font-semibold text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-xs text-muted">Connected to this project.</p>
          )}
        </div>
      </div>

      {onDisconnect && (
        <Button
          variant="secondary"
          size="sm"
          loading={disconnecting}
          onClick={onDisconnect}
          className="mt-4"
        >
          {disconnecting ? 'Removing…' : 'Disconnect'}
        </Button>
      )}
    </div>
  )
}

/** Gmail, Drive and Calendar are one Google consent. This sends the user to Google;
 *  the backend receives the redirect and stores the grant against this project. */
function ConnectGooglePanel({
  projectId,
  status,
}: {
  projectId: string
  status: IntegrationStatus
}) {
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // The deployment has no Google client configured, so there is nothing to connect to.
  if (status.variables.length > 0) {
    return (
      <div className="rounded-xl border border-line bg-raised p-4">
        <p className="text-xs font-semibold text-ink">
          This server has no Google app configured. Add to <code>backend/.env</code>, then
          restart the API:
        </p>
        <ul className="mt-2 space-y-1">
          {status.variables.map((variable) => (
            <li key={variable} className="break-all font-mono text-xs text-muted">
              {variable}=
            </li>
          ))}
        </ul>
        <a
          href={status.setup_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-brand transition-colors duration-150 hover:text-brand-hover"
        >
          Create the OAuth client
          <Icon.External className="h-3.5 w-3.5" />
        </a>
      </div>
    )
  }

  async function connect() {
    setConnecting(true)
    setError(null)
    try {
      const { url } = await api.googleAuthorizeUrl(projectId)
      window.location.href = url
    } catch (caught) {
      setError(errorMessage(caught))
      setConnecting(false)
    }
  }

  return (
    <div className="rounded-xl border border-line bg-raised p-4">
      <p className="text-xs text-muted">
        Connecting Google once gives this project Gmail, Drive and Calendar — they are one
        consent. Only this project can use it.
      </p>
      <Button
        variant="secondary"
        size="sm"
        loading={connecting}
        onClick={connect}
        className="mt-3"
      >
        {connecting ? 'Redirecting…' : 'Connect Google'}
      </Button>
      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
    </div>
  )
}
