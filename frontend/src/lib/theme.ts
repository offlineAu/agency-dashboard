import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'dashboard-theme'

export function storedTheme(): Theme {
  try { return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light' } catch { return 'light' }
}

export function applyTheme(t: Theme) {
  document.documentElement.dataset.theme = t
  try { localStorage.setItem(KEY, t) } catch { /* storage blocked: theme still applies for this visit */ }
  window.dispatchEvent(new CustomEvent('dashboard-theme', { detail: t }))
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [t, setT] = useState<Theme>(() => (document.documentElement.dataset.theme as Theme) || storedTheme())
  useEffect(() => {
    const h = (e: Event) => setT((e as CustomEvent).detail)
    window.addEventListener('dashboard-theme', h)
    return () => window.removeEventListener('dashboard-theme', h)
  }, [])
  return [t, applyTheme]
}
