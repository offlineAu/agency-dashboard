// Thin client for OUR backend. Never talks to Infloww directly; never holds the Infloww key.
const TOKEN_KEY = 'dashboard-token'

export function getToken(): string {
  try { return sessionStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}
export function setToken(t: string) {
  try { if (t) sessionStorage.setItem(TOKEN_KEY, t); else sessionStorage.removeItem(TOKEN_KEY) } catch { /* storage blocked */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

function headers(extra?: Record<string, string>) {
  const h: Record<string, string> = { Accept: 'application/json', ...extra }
  const t = getToken()
  if (t) h['X-Dashboard-Token'] = t
  return h
}

export type Params = Record<string, string | number | boolean | undefined | null>

export function qs(params?: Params) {
  const u = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') u.set(k, String(v)) })
  const s = u.toString()
  return s ? `?${s}` : ''
}

export async function apiGet<T = any>(path: string, params?: Params): Promise<T> {
  const r = await fetch(`/api${path}${qs(params)}`, { headers: headers() })
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* ignore */ }
    if (r.status === 401) window.dispatchEvent(new Event('dashboard-auth-required'))
    throw new ApiError(r.status, msg)
  }
  return r.json()
}

export async function apiSend<T = any>(method: 'POST' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, { method, headers: headers({ 'Content-Type': 'application/json' }), body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* ignore */ }
    throw new ApiError(r.status, msg)
  }
  return r.json()
}

export async function download(path: string, params: Params, filename: string) {
  const r = await fetch(`/api${path}${qs(params)}`, { headers: headers() })
  if (!r.ok) throw new ApiError(r.status, `Export failed (HTTP ${r.status})`)
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

// ---- shared response types (only what the UI relies on)
export interface Growth { value: number | null; reason: string | null }
export interface Coverage { dataset: string; complete: boolean; covered?: number; expected: number; missing_days: number; oldest_fetch: number | null; newest_fetch: number | null }
export interface Meta {
  source: string; configured: boolean; complete: boolean; syncing: boolean
  coverage: Record<string, Coverage>; oldest_fetch: number | null; newest_fetch: number | null; age_s: number | null
  unavailable: Record<string, string>; period: { start: string; end: string; timezone: string }; basis: string
}

/** Fetch a protected image (sends the dashboard token, which a plain <img src> cannot) and return a blob URL. */
export async function apiBlobUrl(path: string): Promise<string | null> {
  const r = await fetch(`/api${path}`, { headers: headers({ Accept: 'image/*' }) })
  if (r.status === 404) return null
  if (!r.ok) throw new ApiError(r.status, `HTTP ${r.status}`)
  return URL.createObjectURL(await r.blob())
}

/** Upload raw image bytes (validated server-side by magic bytes). */
export async function apiUpload(path: string, file: Blob): Promise<any> {
  const r = await fetch(`/api${path}`, { method: 'PUT', headers: headers({ 'Content-Type': file.type || 'application/octet-stream' }), body: file })
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : msg } catch { /* ignore */ }
    throw new ApiError(r.status, msg)
  }
  return r.json()
}
