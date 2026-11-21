import { useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { Camera, Loader2, Trash2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { apiBlobUrl, apiSend, apiUpload } from '../lib/api'
import { useMeta } from '../lib/hooks'

export type AvatarKind = 'creator' | 'employee'

// Decorative identity gradients (not data colours). Picked by a stable hash of the id.
const GRADS = [
  ['#6366f1', '#a855f7'], ['#0ea5e9', '#6366f1'], ['#10b981', '#0ea5e9'], ['#f59e0b', '#ef4444'],
  ['#ec4899', '#8b5cf6'], ['#14b8a6', '#22c55e'], ['#f97316', '#ec4899'], ['#3b82f6', '#06b6d4'],
]

function hash(s: string) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h) }

export function initials(name?: string | null) {
  if (!name) return '?'
  // "Chatter Jane Doe - Jay" -> use the alias after the dash if there is one
  const base = name.includes(' - ') ? name.split(' - ').pop()!.trim() : name.trim()
  const words = base.split(/\s+/).filter(w => /[A-Za-z0-9]/.test(w))
  if (!words.length) return '?'
  return (words.length === 1 ? words[0].slice(0, 2) : words[0][0] + words[words.length - 1][0]).toUpperCase()
}

/** Photo URL for a person, if one was uploaded (photos are local to this server; Infloww has none). */
export function useAvatarUrl(kind: AvatarKind, id?: string | number | null) {
  const meta = useMeta()
  const key = `${kind}:${id}`
  const version = id != null ? meta.data?.avatars?.[key] : undefined
  const q = useQuery({
    queryKey: ['avatar', key, version],
    queryFn: () => apiBlobUrl(`/avatars/${kind}/${id}`),
    enabled: version != null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
  })
  return version != null ? q.data ?? null : null
}

export function Avatar({ kind, id, name, size = 36, className, ring = false }: {
  kind: AvatarKind; id?: string | number | null; name?: string | null; size?: number; className?: string; ring?: boolean
}) {
  const url = useAvatarUrl(kind, id)
  const [a, b] = GRADS[hash(String(id ?? name ?? '')) % GRADS.length]
  const style = { width: size, height: size, fontSize: Math.max(10, Math.round(size * 0.36)) }
  const cls = clsx('inline-grid shrink-0 place-items-center overflow-hidden rounded-full font-semibold text-white select-none', ring && 'ring-2 ring-card', className)
  return url
    ? <img src={url} alt={name || ''} className={clsx(cls, 'object-cover')} style={style} />
    : <span className={cls} style={{ ...style, background: `linear-gradient(135deg, ${a}, ${b})` }} aria-hidden="true">{initials(name)}</span>
}

export function AvatarStack({ people, size = 34, max = 5 }: { people: { kind: AvatarKind; id: string | number; name?: string | null }[]; size?: number; max?: number }) {
  const shown = people.slice(0, max)
  return (
    <div className="flex items-center">
      {shown.map((p, i) => <span key={`${p.kind}${p.id}`} style={{ marginLeft: i ? -size * 0.3 : 0, zIndex: max - i }} className="relative" title={p.name || ''}>
        <Avatar {...p} size={size} ring />
      </span>)}
      {people.length > max && <span className="relative -ml-2 grid place-items-center rounded-full bg-card-2 text-[11px] font-semibold text-ink-2 ring-2 ring-card" style={{ width: size, height: size }}>+{people.length - max}</span>}
    </div>
  )
}

/** Avatar with upload/remove controls. Images are validated server-side (PNG/JPEG/WebP, ≤2 MB). */
export function AvatarEditor({ kind, id, name, size = 56 }: { kind: AvatarKind; id: string | number; name?: string | null; size?: number }) {
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const meta = useMeta()
  const has = meta.data?.avatars?.[`${kind}:${id}`] != null
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setErr(null)
    try { await fn(); await qc.invalidateQueries({ queryKey: ['meta'] }) } catch (e: any) { setErr(e?.message || 'Upload failed') } finally { setBusy(false) }
  }
  return (
    <div className="flex items-center gap-3">
      <button type="button" onClick={() => input.current?.click()} className="group relative rounded-full outline-none focus-visible:ring-4 focus-visible:ring-accent/30"
        aria-label={`${has ? 'Change' : 'Add'} photo for ${name || id}`} title={`${has ? 'Change' : 'Add'} photo`}>
        <Avatar kind={kind} id={id} name={name} size={size} />
        <span className="absolute inset-0 grid place-items-center rounded-full bg-black/45 text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
        </span>
      </button>
      <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
        onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (f) run(() => apiUpload(`/avatars/${kind}/${id}`, f)) }} />
      {has && <button type="button" className="btn-icon size-7" aria-label={`Remove photo for ${name || id}`} title="Remove photo" disabled={busy}
        onClick={() => run(() => apiSend('DELETE', `/avatars/${kind}/${id}`))}><Trash2 size={13} /></button>}
      {err && <span className="text-xs text-bad">{err}</span>}
    </div>
  )
}
