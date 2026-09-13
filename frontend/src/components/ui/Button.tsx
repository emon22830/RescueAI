import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'contrast'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand text-brand-ink hover:bg-brand-hover shadow-card',
  secondary: 'border border-line-strong bg-surface text-ink hover:bg-raised',
  ghost: 'text-muted hover:bg-raised hover:text-ink',
  danger: 'bg-danger text-white hover:opacity-90',
  // The loud marketing call to action — one per screen, never inside the app shell.
  contrast: 'bg-contrast text-contrast-ink hover:bg-contrast-hover shadow-card',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 gap-1.5 px-3 text-xs',
  md: 'h-10 gap-2 px-4 text-sm',
  lg: 'h-12 gap-2 px-6 text-[0.95rem]',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  /** Shows a spinner and blocks the click. Every async action uses this. */
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon,
  disabled,
  className = '',
  children,
  ...rest
}: Props) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner className="h-3.5 w-3.5" /> : icon}
      {children}
    </button>
  )
}
