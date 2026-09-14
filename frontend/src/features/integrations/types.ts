import type { Source } from '../intelligence/types'

/** How an app's credential is supplied.
 *  `token` — pasted on the Connections page and stored encrypted for this project.
 *  `oauth` — one Google client configured on the server in backend/.env, shared by
 *  Gmail, Drive and Calendar until they move to the per-project model. */
export type IntegrationMode = 'token' | 'oauth'

/** Connection status for one app on one project, from
 *  `GET /projects/{id}/integrations`. Never carries a credential value. */
export interface IntegrationStatus {
  id: Source
  mode: IntegrationMode
  connected: boolean
  /** What the app said about itself when the credential was verified — team, repo,
   *  user, or the Google account and the apps one consent covers. */
  metadata: Record<string, string | string[]>
  /** Whether an approved action can be executed here, or the app is read-only. */
  writes_back: boolean
  /** Where the user goes to issue the credential. */
  setup_url: string
  /** oauth apps only: the environment variables still empty on the server. */
  variables: string[]
}

/** What the connect form sends: the credential, plus whatever else that one app needs
 *  to be reachable. Which extras apply to which app is declared in `EXTRA_FIELDS`.
 *  Mirrors ConnectIntegrationRequest in app/api/integrations.py. */
export interface ConnectIntegrationBody {
  token: string
  repo?: string // github
  channel_ids?: string // slack, optional
  site?: string // jira
  email?: string // jira
  project_key?: string // jira, optional
  key?: string // trello — the API key paired with the token
  workspace?: string // asana, optional
}
