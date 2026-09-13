import { Icon } from '../ui/Icon'
import { useTheme } from '../../lib/theme'

const NEXT = {
  light: 'Switch to dark',
  dark: 'Switch to light',
} as const

export function ThemeToggle() {
  const { theme, cycle } = useTheme()
  const Glyph = theme === 'light' ? Icon.Sun : Icon.Moon

  return (
    <button
      type="button"
      onClick={cycle}
      title={NEXT[theme]}
      aria-label={NEXT[theme]}
      className="flex h-9 w-9 items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-raised hover:text-ink"
    >
      <Glyph className="h-[18px] w-[18px]" />
    </button>
  )
}
