/* Interface icons. One 24px grid, 1.7 stroke, currentColor — never an emoji. */

type Props = { className?: string }

function Stroke({ className = 'h-4 w-4', children }: Props & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  )
}

export const Icon = {
  Sun: (p: Props) => (
    <Stroke {...p}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Stroke>
  ),
  Moon: (p: Props) => (
    <Stroke {...p}>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z" />
    </Stroke>
  ),
  Bell: (p: Props) => (
    <Stroke {...p}>
      <path d="M18 8a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" />
      <path d="M13.7 20a2 2 0 0 1-3.4 0" />
    </Stroke>
  ),
  Plus: (p: Props) => (
    <Stroke {...p}>
      <path d="M12 5v14M5 12h14" />
    </Stroke>
  ),
  Refresh: (p: Props) => (
    <Stroke {...p}>
      <path d="M20.5 12a8.5 8.5 0 1 1-2.6-6.1M20.5 4v5h-5" />
    </Stroke>
  ),
  Check: (p: Props) => (
    <Stroke {...p}>
      <path d="m4.5 12.5 5 5 10-11" />
    </Stroke>
  ),
  ArrowRight: (p: Props) => (
    <Stroke {...p}>
      <path d="M4.5 12h15M13 5.5l6.5 6.5L13 18.5" />
    </Stroke>
  ),
  External: (p: Props) => (
    <Stroke {...p}>
      <path d="M14 4h6v6M20 4l-8.5 8.5" />
      <path d="M18 14.5V18a2.5 2.5 0 0 1-2.5 2.5H6A2.5 2.5 0 0 1 3.5 18V8.5A2.5 2.5 0 0 1 6 6h3.5" />
    </Stroke>
  ),
  Warning: (p: Props) => (
    <Stroke {...p}>
      <path d="M10.3 3.9 2.5 17.4A2 2 0 0 0 4.2 20.5h15.6a2 2 0 0 0 1.7-3.1L13.7 3.9a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9.5v4M12 17h.01" />
    </Stroke>
  ),
  Activity: (p: Props) => (
    <Stroke {...p}>
      <path d="M2.5 12h4l2.5-7 6 14 2.5-7h4" />
    </Stroke>
  ),
  Search: (p: Props) => (
    <Stroke {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="m16.2 16.2 4.3 4.3" />
    </Stroke>
  ),
  Plug: (p: Props) => (
    <Stroke {...p}>
      <path d="M9 3v6M15 3v6" />
      <path d="M5.5 9h13v3a6.5 6.5 0 0 1-13 0Z" />
      <path d="M12 18.5V21" />
    </Stroke>
  ),
  Shield: (p: Props) => (
    <Stroke {...p}>
      <path d="M12 2.8 4.5 6v6c0 4.6 3.1 8.1 7.5 9.2 4.4-1.1 7.5-4.6 7.5-9.2V6Z" />
      <path d="m9 12 2.2 2.2L15.5 10" />
    </Stroke>
  ),
  Chevron: (p: Props) => (
    <Stroke {...p}>
      <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
    </Stroke>
  ),
  Clock: (p: Props) => (
    <Stroke {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.3l3.3 2" />
    </Stroke>
  ),
  Play: (p: Props) => (
    <Stroke {...p}>
      <path d="M8 5.6v12.8L19 12 8 5.6Z" />
    </Stroke>
  ),
  Layers: (p: Props) => (
    <Stroke {...p}>
      <path d="m12 3 9 4.8-9 4.8-9-4.8L12 3Z" />
      <path d="m3.8 12.4 8.2 4.4 8.2-4.4M3.8 16.8 12 21.2l8.2-4.4" />
    </Stroke>
  ),
  Users: (p: Props) => (
    <Stroke {...p}>
      <circle cx="9.5" cy="8" r="3.5" />
      <path d="M2.8 20a6.7 6.7 0 0 1 13.4 0" />
      <path d="M16.5 4.8a3.5 3.5 0 0 1 0 6.4M18 13.6A6.7 6.7 0 0 1 21.2 20" />
    </Stroke>
  ),
  Minus: (p: Props) => (
    <Stroke {...p}>
      <path d="M5 12h14" />
    </Stroke>
  ),
  Menu: (p: Props) => (
    <Stroke {...p}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Stroke>
  ),
  Close: (p: Props) => (
    <Stroke {...p}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Stroke>
  ),
  Trash: (p: Props) => (
    <Stroke {...p}>
      <path d="M4.5 7h15M9.5 7V4.8c0-.7.6-1.3 1.3-1.3h2.4c.7 0 1.3.6 1.3 1.3V7" />
      <path d="M6.5 7 7.3 19a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9L17.5 7" />
      <path d="M10 11v6M14 11v6" />
    </Stroke>
  ),
}
