import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'

// Global filters live in the URL so views are shareable and every page agrees on the same slice.
export type Preset = 'today' | 'yesterday' | '7d' | '30d' | '90d' | 'month' | 'last_month' | 'custom'
export const PRESETS: { key: Preset; label: string }[] = [
  { key: 'today', label: 'Today' }, { key: 'yesterday', label: 'Yesterday' }, { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' }, { key: '90d', label: 'Last 90 days' }, { key: 'month', label: 'This month' },
  { key: 'last_month', label: 'Last month' }, { key: 'custom', label: 'Custom range' },
]

const iso = (d: Date) => d.toISOString().slice(0, 10)
// A static snapshot pins "today" to its capture date so its preset ranges match the recorded data.
function utcToday() { const a = (globalThis as any).__SNAPSHOT_TODAY__; const n = a ? new Date(a) : new Date(); return new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate())) }
function addDays(d: Date, n: number) { const x = new Date(d); x.setUTCDate(x.getUTCDate() + n); return x }

export function presetRange(p: Preset): { start: string; end: string } {
  const t = utcToday()
  switch (p) {
    case 'today': return { start: iso(t), end: iso(t) }
    case 'yesterday': return { start: iso(addDays(t, -1)), end: iso(addDays(t, -1)) }
    case '7d': return { start: iso(addDays(t, -6)), end: iso(t) }
    case '90d': return { start: iso(addDays(t, -89)), end: iso(t) }
    case 'month': return { start: iso(new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), 1))), end: iso(t) }
    case 'last_month': {
      const first = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() - 1, 1))
      const last = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), 0))
      return { start: iso(first), end: iso(last) }
    }
    default: return { start: iso(addDays(t, -29)), end: iso(t) }
  }
}

export interface FilterState {
  preset: Preset; start: string; end: string; creators: string[]; basis: 'gross' | 'net'
  params: { start: string; end: string; creators?: string; basis: string }
  setPreset: (p: Preset) => void
  setRange: (start: string, end: string) => void
  setCreators: (ids: string[]) => void
  setBasis: (b: 'gross' | 'net') => void
}

const Ctx = createContext<FilterState | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [sp, setSp] = useSearchParams()
  const preset = (sp.get('range') as Preset) || '30d'
  const range = preset === 'custom' ? { start: sp.get('start') || presetRange('30d').start, end: sp.get('end') || presetRange('30d').end } : presetRange(preset)
  const creators = (sp.get('creators') || '').split(',').filter(Boolean)
  const basis = (sp.get('basis') === 'net' ? 'net' : 'gross') as 'gross' | 'net'

  const update = useCallback((fn: (p: URLSearchParams) => void) => {
    setSp(prev => { const n = new URLSearchParams(prev); fn(n); return n }, { replace: true })
  }, [setSp])

  const value = useMemo<FilterState>(() => ({
    preset, ...range, creators, basis,
    params: { start: range.start, end: range.end, creators: creators.length ? creators.join(',') : undefined, basis },
    setPreset: p => update(n => { n.set('range', p); if (p !== 'custom') { n.delete('start'); n.delete('end') } else { const r = presetRange('30d'); n.set('start', range.start || r.start); n.set('end', range.end || r.end) } }),
    setRange: (s, e) => update(n => { n.set('range', 'custom'); n.set('start', s); n.set('end', e) }),
    setCreators: ids => update(n => { if (ids.length) n.set('creators', ids.join(',')); else n.delete('creators') }),
    setBasis: b => update(n => { if (b === 'net') n.set('basis', 'net'); else n.delete('basis') }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [preset, range.start, range.end, creators.join(','), basis, update])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useFilters() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useFilters outside FilterProvider')
  return v
}

/** Carry global filters across navigation links. */
export function useFilterSearch() {
  const [sp] = useSearchParams()
  const keep = new URLSearchParams()
  for (const k of ['range', 'start', 'end', 'creators', 'basis']) { const v = sp.get(k); if (v) keep.set(k, v) }
  const s = keep.toString()
  return s ? `?${s}` : ''
}
