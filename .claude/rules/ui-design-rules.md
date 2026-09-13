# UI design rules — `frontend/`

The product is an investigator. The interface has to look like something a team would
trust with write access to Linear, Gmail and Calendar. Calm, dense where it matters,
never decorated. Read this before writing a component; `frontend-rules.md` covers
structure, this covers how it looks.

## The one-line brief

> A modern SaaS product: a soft-sky marketing page that shows the real interface, and
> behind sign-in a calm control room — one violet accent, evidence always one click
> away, and nothing on screen that is not a fact.

The app lives at `/app` behind a session. `/` is a public landing page whose job is to
*show the product*, not to describe it: every section leads with the real interface or
the real workflow.

---

## 1 — Tokens, never raw colours

Every colour, radius and shadow is a token defined in `src/index.css`. A component uses
the semantic name, never a Tailwind palette class.

```tsx
✗ <div className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700">
✓ <div className="bg-surface border border-line">
```

If a component needs a colour that does not exist as a token, add the token. Two shades
of the same idea is how a UI starts looking machine-made.

### Semantic surfaces

| Token | Means |
|---|---|
| `bg-canvas` | the page behind everything |
| `bg-surface` | a card, a panel, the top bar |
| `bg-raised` | a nested block inside a card — evidence rows, code, params |
| `border-line` | every divider and card edge |
| `border-line-strong` | an input, a hovered card |
| `text-ink` | headings and primary text |
| `text-muted` | body copy, descriptions |
| `text-faint` | labels, timestamps, metadata |

Each one flips automatically in dark mode. A component never writes `dark:` for a
surface. `dark:` is only allowed for a one-off that no token covers — and that is rare
enough to justify in a comment.

### Accent and status

| Token | Hex (light) | Used for |
|---|---|---|
| `brand` | `#5b54f0` | primary buttons, active nav, links, focus ring, progress fill |
| `brand-soft` | tinted wash | the background behind a brand icon or selected row |
| `danger` | `#e5484d` | critical severity, at-risk health, failed action |
| `warn` | `#e5900a` | high/medium severity, watch health, executing |
| `success` | `#1a9f65` | on-track health, completed action, connected app |
| `info` | `= brand` | neutral notices |
| `contrast` | near-black (inverts in dark) | the one loud marketing CTA per screen |

`contrast` never appears inside the app shell — it is the marketing header and final
call to action only. In dark mode it inverts to near-white, because black on near-black
would vanish.

**One accent per region.** A card may carry a status colour *or* the brand colour, never
both. A screen that uses four accents at once looks generated.

---

## 2 — Typography

`Plus Jakarta Sans` for everything, loaded in `index.html`. One family across the
marketing page and the app. No second display face, no mono except real machine output
(an id, a variable name, a token, an API result).

| Role | Class | Notes |
|---|---|---|
| Marketing display | `text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.08]` | the hero headline, once |
| Section headline | `text-3xl sm:text-[2.6rem] font-extrabold tracking-tight` | one per landing section |
| Page title | `text-2xl font-extrabold tracking-tight` | one per app page |
| Section title | `text-base font-semibold` | card and section headers |
| Body | `text-sm` | the app default — 14px, not 16 |
| Secondary | `text-sm text-muted` | descriptions, agent prose |
| Metadata | `text-xs text-faint` | timestamps, counts, source names |
| Label | `text-[11px] font-semibold uppercase tracking-[0.08em] text-faint` | stat captions only |
| Metric | `text-3xl font-semibold tabular-nums tracking-tight` | stat tiles |

Rules:
- **Two weights per component, maximum** — one emphasis weight against normal.
- **In the app, semibold is the top of the scale.** Dense UI does not need more.
- **On the marketing page, `font-extrabold` is the display weight** and only headlines
  and the eyebrow get it. The template's headings are heavy; its body copy is not.
- `tabular-nums` on every number that can change, so it does not jitter on re-render.
- `tracking-tight` on anything `text-2xl` or larger. Large text at default tracking is
  the clearest tell of an untuned interface.
- Sentence case everywhere. Uppercase is reserved for the label role above.

---

## 3 — Shape, depth, spacing

- **Radius:** `rounded-xl` (12px) for app cards and panels, `rounded-2xl` (16px) for
  marketing cards and the floating header, `rounded-lg` (10px) for buttons, inputs and
  nested blocks, `rounded-full` for pills and avatars. Nothing square, nothing
  pill-shaped that is not a pill.
- **Depth is a border, not a shadow.** Cards get `border border-line`. `shadow-card` is
  allowed on the top bar and on hover; nothing else. In dark mode shadows are invisible
  anyway — the border is what carries the elevation, which is why it comes first.
- **Spacing is a 4px scale.** Card padding `p-5`, section gap `space-y-6`, grid gap
  `gap-4`, related items `gap-2`/`gap-3`.
- **Page width `max-w-6xl`, gutter `px-6`** — the same measure on both the marketing
  page and the app, so the product feels like one thing. Never full-bleed.
- **Marketing section rhythm:** `py-20 sm:py-24`, headline block then a `mt-14` grid.
  Alternate `bg-surface` and `bg-canvas` between bands so the page has structure
  without dividers everywhere.
- Give a section room above it (`pt-2` minimum beyond the stack gap) so headings group
  with what they label, not with what came before.

---

## 4 — Motion

- `transition-colors duration-150` on anything hoverable. That is the default.
- `duration-200` for a panel opening or a height change.
- Only two animations exist: the spinner, and a running agent's pulse.
- No entrance animation, no stagger, no parallax, no scroll-triggered reveal. This is a
  tool someone opens twenty times a day.

---

## 5 — Dark mode

Class-based: `document.documentElement.classList.toggle('dark')`, preference in
`localStorage`, default `system`. The no-flash script in `index.html` runs before paint —
do not remove it.

- Dark is a **real design**, not inverted light. Surfaces get *lighter* as they come
  forward (`canvas` → `surface` → `raised`); never pure black, never pure white text.
- Status colours get their own dark values so they stay legible on a dark surface — this
  is already handled in the token block. Do not hand-pick a lighter red in a component.
- Check both themes before calling a screen done. A component that only works in light
  mode is unfinished.

---

## 6 — Every state is designed

An async surface has four states and all four exist in code:

| State | What renders |
|---|---|
| Loading | a skeleton in the shape of the result — never a bare "Loading…" |
| Error | `<Alert tone="danger">` with the real message from the API |
| Empty | `<EmptyState>` — what this panel will show, and the action that fills it |
| Ready | the content |

The empty state is not filler. `backend/.env` is unset most of the time, so **empty is
the state a reviewer sees first.** It must explain the system rather than apologise.

Never substitute placeholder content for a state you have not handled — no fake project,
no sample finding, no "—" standing in for a number the API did not send. `null` progress
renders as "Not measured", not as `0%`.

---

## 7 — Product-specific rules

These come from what the product is, and they outrank visual preference.

1. **Evidence is always one interaction from a finding.** The "Why?" disclosure is the
   feature. It is never behind a route change.
2. **A source is named and linked.** Every piece of evidence shows its app icon, its
   title, and — when the API gave one — a link out to the real message, issue or doc.
3. **Approval reads as consequential.** The recovery plan states what will be written and
   where, before the button. The button says what it will do and to how many things
   (`Approve & execute 3 actions`), never just "Confirm".
4. **Health has one vocabulary.** `on_track` → "On track", `watch` → "Watch",
   `at_risk` → "At risk". Same words, same colour, on every screen.
5. **An unconfigured app says what is missing.** Name the environment variable. Never
   render a disconnected app as connected, and never show a value from `.env`.
6. **Agent activity is a log, not a story.** One row per node: which agent, what it
   found, how many items, when. Show failures as plainly as successes.

---

## 7b — Navigation and the app shell

The app is a sidebar shell, not a page with a top bar. `AppLayout` owns it.

- **Left rail, 16rem, sticky full height.** Brand, `Overview`, then the project list.
  The project you are looking at expands to show its own pages (`Overview`,
  `Connections`) so nothing inside a project is reachable only by a button on another
  page.
- **A health dot next to every project in the rail.** Which project is on fire should be
  answerable without opening anything.
- **Below `lg` the rail becomes a drawer** behind a hamburger, and it closes on every
  route change — otherwise it covers the page you just opened.
- **One source of truth for the project list.** `AppLayout` loads it and passes it down
  through the router's outlet context (`lib/appData.ts`). The sidebar and the dashboard
  must never fetch it separately, or creating a project shows up in one and not the
  other.
- **The URL carries intent.** `?new=1` opens the create form, and closing it clears the
  param — a refresh must not reopen something you dismissed.
- Icons mean what they look like: a hamburger opens navigation, an X closes it. Never a
  decorative glyph for a control.

## 8 — Things that make a UI look AI-generated

Do none of these.

- Gradient **text**, purple→pink anything, glow or neon. The `.hero-sky` background is
  the single sanctioned gradient in the codebase: it belongs to the marketing hero, the
  integrations band, the final CTA and the sign-in page, and never to an app surface.
- Emoji used as an icon. Icons are inline SVG in `components/ui/`.
- Glassmorphism on cards. `backdrop-blur` exists only on the two sticky headers.
- Everything centred. Content is left-aligned in a grid; only empty states centre.
- A shadow on every element.
- Three sizes of the same button on one screen.
- Decorative hero copy in an app view. Marketing tone belongs on a marketing page and
  this product does not have one.
- Rounded-full containers that are not pills, or `rounded-3xl` cards.
- Filler counts, fake sparklines, invented trend arrows. Every number in the app came
  from the API.
- **Fabricated social proof.** No invented testimonials, named customers, star ratings,
  logo walls or "trusted by N teams". The template has them; we do not get to. The
  landing page persuades by showing the product working, and the one illustration of the
  interface is labelled *Example project* inside its own frame.

---

## 9 — Component budget

`components/ui/` holds the primitives — `Button`, `Card`, `Badge`, `StatTile`,
`ProgressBar`, `Alert`, `EmptyState`, `Spinner`, `Icon`, `SourceIcon`. A page composes
them and a feature folder composes them into product pieces.

`features/marketing/` holds the landing page: one file per band (`Hero`,
`ProblemSection`, `HowItWorks`, `FeatureSection`, `UseCases`, `IntegrationGrid`,
`FaqSection`, `FinalCta`), plus `Section` for the shared wrapper and `Wordmark` for the
mark the app shell also uses. `LandingPage.tsx` only orders them.

- A component file over ~120 lines is doing two jobs. Split it.
- A page that renders JSX for a domain object directly is missing a feature component.
- New primitive only when a second screen needs it. One-offs live where they are used.

## Checks

`npm run build` type-checks and builds; it must pass. Then open both themes at 1440px
and at 390px before you call it done — the marketing page and the app both.
