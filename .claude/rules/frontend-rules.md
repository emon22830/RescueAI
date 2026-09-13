# Frontend rules

## Structure
- `pages/` = screens, one per route.
- `features/` = product functionality, grouped by domain.
- `components/ui/` = reusable presentational pieces. `components/layout/` = shell.
- `lib/api.ts` = every HTTP call. A `fetch` anywhere else is a bug.

## Types
- Response types live in `features/*/types.ts` and mirror
  `.claude/context/04-api-contracts.md`.
- No `any`. Union literals for enums (`'low' | 'medium' | 'high' | 'critical'`).

## State
- `useState` and `useEffect` are enough. No Redux, no Zustand, no React Query.
- Load in the page, pass down as props.

## UI
- Tailwind utility classes. No CSS files beyond `index.css`.
- Colour, type, spacing, radius and dark mode are defined in
  `.claude/rules/ui-design-rules.md`. Read it before writing a component.
- Semantic tokens only — `bg-surface`, `text-muted`, `border-line`. Never `bg-white`,
  never a `dark:` class for a surface.
- Every async surface handles four states: loading, error, empty, ready.
- Evidence is always reachable from a finding. "Why?" is the product.

## Checks
`npm run build` must pass — it type-checks and builds. Run it before committing.
