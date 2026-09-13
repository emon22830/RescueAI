import { Card } from '../components/ui/Card'
import { PROVIDERS } from '../features/integrations/providers'

export function ConnectionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Connections</h1>
        <p className="mt-1 text-sm text-slate-600">
          The apps the agent investigates. Credentials live in <code>backend/.env</code>.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {PROVIDERS.map((provider) => (
          <Card key={provider.id}>
            <h2 className="font-medium">{provider.label}</h2>
            <p className="text-sm text-slate-600">{provider.investigates}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}
