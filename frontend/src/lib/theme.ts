import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'rescue-theme'

function prefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Read the saved preference. Falls back to the OS setting when nothing is saved yet
 * or storage is unavailable — there is no third "system" choice to switch back to,
 * this is just where a first-time visitor's toggle starts. */
function stored(): Theme {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    /* private mode — fall through to the OS preference */
  }
  return prefersDark() ? 'dark' : 'light'
}

function apply(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

/**
 * Light / dark, persisted. The class itself is set before first paint by the script in
 * index.html; this keeps it in sync once React is running.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(stored)

  useEffect(() => {
    apply(theme)
    try {
      localStorage.setItem(KEY, theme)
    } catch {
      /* private mode — the choice just will not survive a reload */
    }
  }, [theme])

  const cycle = useCallback(() => {
    setTheme((current) => (current === 'light' ? 'dark' : 'light'))
  }, [])

  return { theme, setTheme, cycle }
}
