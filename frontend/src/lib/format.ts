// Formatting. All money from the backend is in the smallest currency unit (cents).
let currency = 'USD'
export function setCurrency(c: string) { currency = c || 'USD' }

export function money(cents: number | null | undefined, opts: { compact?: boolean; sign?: boolean } = {}): string {
  if (cents === null || cents === undefined || Number.isNaN(cents)) return '—'
  const v = cents / 100
  const abs = Math.abs(v)
  const fmt = new Intl.NumberFormat('en-US', {
    style: 'currency', currency,
    notation: opts.compact && abs >= 10000 ? 'compact' : 'standard',
    maximumFractionDigits: opts.compact && abs >= 10000 ? 1 : abs >= 1000 ? 0 : 2,
    minimumFractionDigits: opts.compact && abs >= 10000 ? 0 : abs >= 1000 ? 0 : 2,
    signDisplay: opts.sign ? 'exceptZero' : 'auto',
  })
  return fmt.format(v)
}

export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(n)
}

export function compact(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(n)
}

export function pct(n: number | null | undefined, digits = 1, sign = false): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return `${sign && n > 0 ? '+' : ''}${n.toFixed(digits)}%`
}

export function duration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—'
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(0)}s`
  if (s < 3600) return `${(s / 60).toFixed(1)}m`
  return `${(s / 3600).toFixed(1)}h`
}

export function ago(ts: number | null | undefined): string {
  if (!ts) return 'never'
  const s = Date.now() / 1000 - ts
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export function shortDate(iso: string): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  if (!d) return `${MON[m - 1]} ${y}`
  return `${MON[m - 1]} ${d}`
}
export function longDate(iso: string): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return `${MON[m - 1]} ${d}, ${y}`
}
export function msDate(ms: number | string | null | undefined): string {
  if (!ms) return '—'
  const d = new Date(Number(ms))
  return `${MON[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`
}
export function tsTime(ts: number | null | undefined): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
