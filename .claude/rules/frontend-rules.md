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
- Every async action needs a visible loading state and a visible error state.
- Evidence is always reachable from a finding. "Why?" is the product.

## Checks
`npm run build` must pass — it type-checks and builds. Run it before committing.
