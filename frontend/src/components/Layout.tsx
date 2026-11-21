import clsx from 'clsx'
import {
  Activity, BarChart3, Bell, CalendarDays, Check, ChevronDown, CircleDollarSign, FileText, Heart, LayoutDashboard, Megaphone, Menu,
  MessagesSquare, Moon, Search, Settings, ShieldCheck, Sparkles, Sun, Users, X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { longDate, setCurrency } from '../lib/format'
import { PRESETS, useFilters, useFilterSearch } from '../lib/filters'
import { useMeta } from '../lib/hooks'
import { useTheme } from '../lib/theme'
import { Avatar } from './Avatar'
import { Segmented } from './ui'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/creators', label: 'Creators', icon: Sparkles },
  { to: '/chatters', label: 'Chatters', icon: MessagesSquare },
  { to: '/fans', label: 'Fans', icon: Heart },
  { to: '/revenue', label: 'Revenue', icon: CircleDollarSign },
  { to: '/marketing', label: 'Marketing', icon: Megaphone },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/reports', label: 'Reports', icon: FileText },
]
const NAV2 = [
  { to: '/status', label: 'API Status', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function useOutside(ref: React.RefObject<HTMLElement | null>, cb: () => void) {
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) cb() }
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') cb() }
    document.addEventListener('mousedown', h); document.addEventListener('keydown', k)
    return () => { document.removeEventListener('mousedown', h); document.removeEventListener('keydown', k) }
  }, [ref, cb])
}

function Popover({ button, children, align = 'left', width = 'w-64' }: { button: (open: boolean) => ReactNode; children: (close: () => void) => ReactNode; align?: 'left' | 'right'; width?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useOutside(ref, () => setOpen(false))
  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen(o => !o)}>{button(open)}</div>
      {open && <div className={clsx('absolute top-full z-40 mt-2 rounded-2xl border border-line bg-card p-1.5 shadow-xl', width, align === 'right' ? 'right-0' : 'left-0')}>{children(() => setOpen(false))}</div>}
    </div>
  )
}

const itemCls = 'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] text-ink-2 hover:bg-ink/5'

function DateFilter() {
  const f = useFilters()
  const [s, setS] = useState(f.start)
  const [e, setE] = useState(f.end)
  useEffect(() => { setS(f.start); setE(f.end) }, [f.start, f.end])
  const label = PRESETS.find(p => p.key === f.preset)?.label
  return (
    <Popover width="w-72" button={open => (
      <button className={clsx('btn', open && 'border-accent/60 text-ink')} aria-haspopup="dialog">
        <CalendarDays size={15} className="text-accent" /><span className="hidden sm:inline">{f.preset === 'custom' ? `${longDate(f.start)} – ${longDate(f.end)}` : label}</span>
        <span className="sm:hidden">{f.preset === 'custom' ? 'Custom' : label}</span><ChevronDown size={14} />
      </button>
    )}>
      {close => (
        <div>
          {PRESETS.filter(p => p.key !== 'custom').map(p => (
            <button key={p.key} onClick={() => { f.setPreset(p.key); close() }} className={itemCls}>
              <span className={clsx(f.preset === p.key && 'font-semibold text-ink')}>{p.label}</span>{f.preset === p.key && <Check size={15} strokeWidth={3} className="text-accent" />}
            </button>
          ))}
          <div className="mt-1.5 border-t border-line px-1 pt-2.5 pb-1">
            <div className="mb-1.5 text-[11px] font-medium tracking-wide text-ink-3 uppercase">Custom range (UTC)</div>
            <div className="flex items-center gap-1.5">
              <input type="date" className="input w-full px-2 text-xs" value={s} max={e} onChange={ev => setS(ev.target.value)} aria-label="Start date" />
              <span className="text-ink-3">–</span>
              <input type="date" className="input w-full px-2 text-xs" value={e} min={s} onChange={ev => setE(ev.target.value)} aria-label="End date" />
            </div>
            <button className="btn-primary mt-2 w-full justify-center" disabled={!s || !e || s > e} onClick={() => { f.setRange(s, e); close() }}>Apply</button>
          </div>
        </div>
      )}
    </Popover>
  )
}

function CreatorFilter({ creators }: { creators: { id: string; name: string; connected: number }[] }) {
  const f = useFilters()
  const [q, setQ] = useState('')
  const sel = new Set(f.creators)
  const list = creators.filter(c => c.connected && (c.name || '').toLowerCase().includes(q.toLowerCase()))
  const label = sel.size === 0 ? 'All creators' : sel.size === 1 ? (creators.find(c => sel.has(c.id))?.name || '1 creator') : `${sel.size} creators`
  return (
    <Popover button={open => <button className={clsx('btn', open && 'border-accent/60 text-ink', sel.size && 'border-accent/40 text-ink')}><Users size={15} className="text-accent" />{label}<ChevronDown size={14} /></button>}>
      {() => (
        <div>
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Find creator…" className="input mb-1.5 w-full" aria-label="Find creator" />
          <button onClick={() => f.setCreators([])} className={itemCls}>
            <span className={clsx(!sel.size && 'font-semibold text-ink')}>All creators</span>{!sel.size && <Check size={15} strokeWidth={3} className="text-accent" />}
          </button>
          <div className="max-h-64 overflow-y-auto">
            {list.map(c => (
              <button key={c.id} onClick={() => { const n = new Set(sel); if (n.has(c.id)) n.delete(c.id); else n.add(c.id); f.setCreators([...n]) }} className={itemCls}>
                <span className="flex min-w-0 items-center gap-2"><Avatar kind="creator" id={c.id} name={c.name} size={24} /><span className={clsx('truncate', sel.has(c.id) && 'font-semibold text-ink')}>{c.name}</span></span>
                {sel.has(c.id) && <Check size={15} strokeWidth={3} className="text-accent" />}
              </button>
            ))}
            {!list.length && <div className="px-2.5 py-3 text-xs text-ink-3">No connected creators{q ? ' match' : ' synced yet'}.</div>}
          </div>
        </div>
      )}
    </Popover>
  )
}

/** Jump to a creator, chatter or page. "/" focuses it. */
function QuickSearch({ meta }: { meta: any }) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const nav = useNavigate()
  const search = useFilterSearch()
  useOutside(ref, () => setOpen(false))
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)) { e.preventDefault(); input.current?.focus() }
    }
    document.addEventListener('keydown', k)
    return () => document.removeEventListener('keydown', k)
  }, [])
  const results = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return []
    const pages = [...NAV, ...NAV2].filter(n => n.label.toLowerCase().includes(s)).map(n => ({ key: 'p' + n.to, to: n.to, label: n.label, kind: 'Page' as const, id: '' }))
    const cr = (meta?.creators || []).filter((c: any) => `${c.name} ${c.user_name}`.toLowerCase().includes(s)).slice(0, 6)
      .map((c: any) => ({ key: 'c' + c.id, to: `/creators/${c.id}`, label: c.name, kind: 'Creator' as const, id: c.id }))
    const em = (meta?.employees || []).filter((e: any) => (e.name || '').toLowerCase().includes(s)).slice(0, 6)
      .map((e: any) => ({ key: 'e' + e.employee_id, to: `/chatters/${e.employee_id}`, label: e.name, kind: 'Chatter' as const, id: e.employee_id }))
    return [...pages, ...cr, ...em]
  }, [q, meta])
  const go = (to: string) => { nav(`${to}${search}`); setQ(''); setOpen(false); input.current?.blur() }
  return (
    <div className="relative" ref={ref}>
      <label className="flex items-center gap-2 rounded-xl border border-line-2 bg-card px-3 py-2 text-[13px] text-ink-3 focus-within:border-accent/60 focus-within:ring-4 focus-within:ring-accent/10">
        <Search size={15} />
        <input ref={input} value={q} onChange={e => { setQ(e.target.value); setOpen(true) }} onFocus={() => setOpen(true)}
          onKeyDown={e => { if (e.key === 'Enter' && results[0]) go(results[0].to) }}
          placeholder="Search creators, chatters…" aria-label="Search creators, chatters and pages" className="w-40 min-w-0 bg-transparent text-ink outline-none placeholder:text-ink-3 xl:w-52" />
        <kbd className="hidden rounded-md border border-line-2 px-1.5 text-[10px] text-ink-3 xl:inline">/</kbd>
      </label>
      {open && q.trim() && (
        <div className="absolute right-0 top-full z-40 mt-2 w-80 rounded-2xl border border-line bg-card p-1.5 shadow-xl">
          {results.length ? results.map(r => (
            <button key={r.key} onClick={() => go(r.to)} className={itemCls}>
              <span className="flex min-w-0 items-center gap-2.5">
                {r.kind === 'Page' ? <span className="grid size-7 place-items-center rounded-full bg-accent/10 text-accent"><LayoutDashboard size={14} /></span>
                  : <Avatar kind={r.kind === 'Creator' ? 'creator' : 'employee'} id={r.id} name={r.label} size={28} />}
                <span className="truncate font-medium text-ink">{r.label}</span>
              </span>
              <span className="text-[11px] text-ink-3">{r.kind}</span>
            </button>
          )) : <div className="px-3 py-3 text-xs text-ink-3">No matches for “{q}”.</div>}
        </div>
      )}
    </div>
  )
}

function ThemeSwitch() {
  const [t, setT] = useTheme()
  return (
    <div role="radiogroup" aria-label="Theme" className="grid grid-cols-2 gap-1 rounded-xl bg-card-2 p-1 ring-1 ring-line">
      {(['light', 'dark'] as const).map(v => (
        <button key={v} role="radio" aria-checked={t === v} onClick={() => setT(v)}
          className={clsx('flex items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-medium transition-colors',
            t === v ? 'bg-accent text-white shadow-sm shadow-accent/30' : 'text-ink-3 hover:text-ink')}>
          {v === 'light' ? <Sun size={13} /> : <Moon size={13} />}{v === 'light' ? 'Light' : 'Dark'}
        </button>
      ))}
    </div>
  )
}

function greeting() {
  const h = new Date().getHours()
  return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

/** Decorative illustration for the sidebar status card (pure SVG, no external assets). */
function Orbit() {
  return (
    <svg viewBox="0 0 120 120" className="pointer-events-none absolute -right-6 -bottom-8 size-32 opacity-90" aria-hidden="true">
      <defs><radialGradient id="orb" cx="35%" cy="30%"><stop offset="0%" stopColor="#fff" stopOpacity=".9" /><stop offset="100%" stopColor="#fff" stopOpacity=".05" /></radialGradient></defs>
      <circle cx="60" cy="60" r="28" fill="url(#orb)" />
      <ellipse cx="60" cy="60" rx="54" ry="16" fill="none" stroke="#fff" strokeOpacity=".35" strokeWidth="2" transform="rotate(-24 60 60)" />
      <circle cx="104" cy="44" r="5" fill="#fff" fillOpacity=".8" /><circle cx="18" cy="80" r="3" fill="#fff" fillOpacity=".6" />
    </svg>
  )
}

export function Layout() {
  const meta = useMeta()
  const f = useFilters()
  const search = useFilterSearch()
  const loc = useLocation()
  const [theme, setTheme] = useTheme()
  const [mobile, setMobile] = useState(false)
  useEffect(() => setMobile(false), [loc.pathname])
  useEffect(() => { if (meta.data?.currency) setCurrency(meta.data.currency) }, [meta.data?.currency])
  const showFilters = !['/status', '/settings'].includes(loc.pathname)
  const alerts = meta.data?.alerts || 0
  const configured = meta.data?.configured

  const nav = (
    <nav className="flex h-full flex-col overflow-y-auto p-4">
      <Link to={{ pathname: '/', search }} className="mb-7 flex items-center gap-3 px-2 pt-1">
        <div className="grid size-10 place-items-center rounded-2xl bg-gradient-to-br from-accent to-[#8b5cf6] shadow-lg shadow-accent/30">
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="white" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 17l5-6 4 4 7-9" /></svg>
        </div>
        <div><div className="text-[16px] leading-tight font-bold tracking-tight">Agency Intelligence</div><div className="text-[11px] text-ink-3">Powered by Infloww API</div></div>
      </Link>
      <div className="mb-2 px-3 text-[11px] font-semibold tracking-wider text-ink-3 uppercase">Main menu</div>
      <div className="space-y-1">{NAV.map(n => <NavItem key={n.to} {...n} search={search} />)}</div>
      <div className="mt-6 mb-2 px-3 text-[11px] font-semibold tracking-wider text-ink-3 uppercase">System</div>
      <div className="space-y-1">{NAV2.map(n => <NavItem key={n.to} {...n} search={search} badge={n.to === '/status' && alerts ? alerts : undefined} />)}</div>
      <div className="mt-auto pt-6">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-accent to-[#8b5cf6] p-4 text-white shadow-lg shadow-accent/25">
          <Orbit />
          <div className="relative">
            <div className="flex items-center gap-1.5 text-[13px] font-semibold"><ShieldCheck size={15} />{configured ? 'Read-only API access' : 'API not configured'}</div>
            <p className="mt-1 max-w-[11rem] text-[11px] leading-relaxed text-white/80">All times UTC. Infloww data lags OnlyFans by 1–24h depending on the report.</p>
            <Link to={{ pathname: '/status', search }} className="mt-3 inline-flex items-center rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-[#4338ca] shadow-sm hover:bg-white/90">View API status</Link>
          </div>
        </div>
        <div className="mt-4"><ThemeSwitch /></div>
      </div>
    </nav>
  )

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-line bg-sidebar lg:block">{nav}</aside>
      {mobile && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={() => setMobile(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-line bg-sidebar shadow-2xl">{nav}</aside>
        </div>
      )}
      <div className="min-w-0 flex-1">
        {meta.data?.fixture_mode && (
          <div className="bg-warn px-4 py-1.5 text-center text-xs font-semibold text-black">FIXTURE DATA — synthetic development dataset, not from Infloww. Do not use for decisions.</div>
        )}
        {meta.data && !configured && (
          <div className="border-b border-bad/30 bg-bad/10 px-4 py-2 text-center text-xs text-bad">Infloww credentials are not configured on the backend. Set INFLOWW_API_KEY and INFLOWW_AGENCY_OID in backend/.env — no data will be shown until then.</div>
        )}
        <header className="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-3 gap-y-2.5 px-4 py-3 sm:px-6">
            <button className="btn-icon lg:hidden" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu size={17} /></button>
            <div className="mr-auto min-w-0">
              <div className="truncate text-[17px] font-semibold tracking-tight">{greeting()}</div>
              <div className="truncate text-xs text-ink-3 tabular">{showFilters ? `${longDate(f.start)} – ${longDate(f.end)} · UTC` : 'System & configuration'}</div>
            </div>
            {showFilters && (
              <div className="order-last flex w-full flex-wrap items-center gap-2 2xl:order-none 2xl:w-auto">
                <DateFilter />
                <CreatorFilter creators={meta.data?.creators || []} />
                <Segmented size="sm" value={f.basis} onChange={f.setBasis} options={[{ value: 'gross', label: 'Gross' }, { value: 'net', label: 'Net' }]} />
              </div>
            )}
            <div className="flex items-center gap-2">
              <div className="hidden md:block"><QuickSearch meta={meta.data} /></div>
              <button className="btn-icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} title="Toggle theme">
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              </button>
              <Link to={{ pathname: '/status', search }} className="btn-icon relative" aria-label={alerts ? `${alerts} sync issues — open API status` : 'No sync issues — open API status'} title={alerts ? `${alerts} sync issue(s)` : 'No sync issues'}>
                <Bell size={16} />
                {alerts > 0 && <span className="absolute -top-1 -right-1 grid min-w-4 place-items-center rounded-full bg-bad px-1 text-[10px] font-bold text-white ring-2 ring-bg">{alerts}</span>}
              </Link>
              <div className="hidden items-center gap-2.5 border-l border-line pl-3 sm:flex">
                <span className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-accent to-[#8b5cf6] text-xs font-bold text-white">AG</span>
                <div className="hidden leading-tight xl:block"><div className="text-[13px] font-semibold">Agency</div><div className="text-[11px] text-ink-3">Read-only access</div></div>
              </div>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 sm:py-7"><Outlet /></main>
      </div>
      {mobile && <button className="fixed top-3 right-3 z-[60] btn-icon lg:hidden" aria-label="Close navigation" onClick={() => setMobile(false)}><X size={16} /></button>}
    </div>
  )
}

function NavItem({ to, label, icon: Icon, end, search, badge }: { to: string; label: string; icon: any; end?: boolean; search: string; badge?: number }) {
  return (
    <NavLink to={{ pathname: to, search }} end={end}
      className={({ isActive }) => clsx('flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13.5px] font-medium transition-all',
        isActive ? 'bg-accent text-white shadow-md shadow-accent/25' : 'text-ink-2 hover:bg-ink/5 hover:text-ink')}>
      {({ isActive }) => <>
        <Icon size={18} className={isActive ? 'text-white' : 'text-ink-3'} />{label}
        {badge ? <span className={clsx('ml-auto rounded-full px-1.5 text-[11px] font-semibold', isActive ? 'bg-white/20 text-white' : 'bg-bad/10 text-bad')}>{badge}</span> : null}
      </>}
    </NavLink>
  )
}
