import clsx from 'clsx'
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Info, Loader2, Minus, RefreshCw, XCircle } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { Growth, Meta } from '../lib/api'
import { ago, pct } from '../lib/format'

export function Card({ title, subtitle, action, children, className, pad = true }: {
  title?: ReactNode; subtitle?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; pad?: boolean
}) {
  return (
    <section className={clsx('card rise', className)}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className={clsx(pad && 'p-5', title && pad && 'pt-4')}>{children}</div>
    </section>
  )
}

export function Delta({ g, invert = false, label }: { g?: Growth | null; invert?: boolean; label?: string }) {
  if (!g) return null
  if (g.value === null) return <span className="delta-none inline-flex items-center gap-1 text-xs text-ink-3" title={g.reason || ''}><Minus size={12} />{g.reason === 'previous period was zero' ? 'new vs. zero' : 'no comparison'}</span>
  const up = g.value >= 0
  const good = invert ? !up : up
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className={clsx('delta inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-semibold tabular', good ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad')}>
        {up ? <ArrowUpRight size={12} strokeWidth={2.5} /> : <ArrowDownRight size={12} strokeWidth={2.5} />}{pct(Math.abs(g.value))}
      </span>
      {label && <span className="delta-label text-ink-3">{label}</span>}
    </span>
  )
}

export function Kpi({ label, value, sub, delta, icon, tone = 'accent', tip, unavailable, spark, featured = false }: {
  label: string; value: ReactNode; sub?: ReactNode; delta?: ReactNode; icon?: ReactNode; tone?: 'accent' | 's1' | 's3' | 's4' | 's5' | 's7'
  tip?: string; unavailable?: string; spark?: ReactNode; featured?: boolean
}) {
  const toneCls = { accent: 'bg-accent/10 text-accent', s1: 'bg-s1/12 text-s1', s3: 'bg-s3/12 text-s3', s4: 'bg-s4/15 text-s4', s5: 'bg-s5/15 text-s5', s7: 'bg-s7/12 text-s7' }[tone]
  return (
    <div className={clsx('rise relative overflow-hidden rounded-2xl border p-4 sm:p-5',
      featured
        ? 'border-transparent bg-gradient-to-br from-accent via-accent to-[#8b5cf6] text-white shadow-lg shadow-accent/25 [&_.delta]:bg-white/20 [&_.delta]:text-white [&_.delta-label]:text-white/75 [&_.delta-none]:text-white/75 [&_[role=tooltip]]:text-ink-2'
        : 'card')}>
      {featured && <div aria-hidden="true" className="pointer-events-none absolute -top-16 -right-10 size-44 rounded-full bg-white/10" />}
      <div className="relative flex items-center gap-3">
        {icon && <div className={clsx('grid size-10 shrink-0 place-items-center rounded-xl', featured ? 'bg-white/15 text-white' : toneCls)}>{icon}</div>}
        <div className={clsx('flex min-w-0 items-center gap-1.5 text-[13px] font-medium', featured ? 'text-white/85 [&_button]:text-white/70' : 'text-ink-2')}>
          <span className="truncate">{label}</span>{tip && <InfoTip text={tip} />}
        </div>
      </div>
      {unavailable ? (
        <div className="relative mt-4"><div className={clsx('text-2xl font-semibold', featured ? 'text-white/70' : 'text-ink-3')}>—</div><div className={clsx('mt-1 text-xs', featured ? 'text-white/75' : 'text-ink-3')}>{unavailable}</div></div>
      ) : (
        <>
          <div className="relative mt-4 flex items-end justify-between gap-3">
            <div className="text-[27px] leading-none font-semibold tracking-tight tabular">{value}</div>
            {spark && <div className="w-24 shrink-0 sm:w-28">{spark}</div>}
          </div>
          <div className={clsx('relative mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs', featured ? 'text-white/80' : 'text-ink-3')}>{delta}{sub}</div>
        </>
      )}
    </div>
  )
}

export function InfoTip({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="relative inline-flex" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={text} className="text-ink-3 hover:text-ink-2 focus:text-ink-2 outline-none" onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
        <Info size={13} />
      </button>
      {open && <span role="tooltip" className="absolute left-1/2 top-5 z-50 w-64 -translate-x-1/2 rounded-lg border border-line-2 bg-card-2 p-2.5 text-xs leading-relaxed font-normal text-ink-2 shadow-xl">{text}</span>}
    </span>
  )
}

export function Badge({ children, tone = 'neutral', title }: { children: ReactNode; tone?: 'neutral' | 'good' | 'bad' | 'warn' | 'accent' | 'info'; title?: string }) {
  const cls = {
    neutral: 'bg-ink/5 text-ink-2 border-line-2', good: 'bg-good/10 text-good border-good/25', bad: 'bg-bad/10 text-bad border-bad/25',
    warn: 'bg-warn/10 text-warn border-warn/25', accent: 'bg-accent/10 text-accent border-accent/25', info: 'bg-s1/10 text-s1 border-s1/25',
  }[tone]
  return <span title={title} className={clsx('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap', cls)}>{children}</span>
}

export function Skeleton({ className }: { className?: string }) { return <div className={clsx('skeleton', className)} /> }

export function PageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="h-80" />
      <div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-64" /><Skeleton className="h-64" /></div>
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error)
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-bad/25 bg-bad/5 p-10 text-center">
      <XCircle className="text-bad" />
      <div><div className="font-medium">Couldn't load this view</div><div className="mt-1 text-sm text-ink-2">{msg}</div></div>
      {onRetry && <button onClick={onRetry} className="btn">Retry</button>}
    </div>
  )
}

export function Empty({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div className="text-ink-3">{icon || <Info size={20} />}</div>
      <div className="text-sm font-medium text-ink-2">{title}</div>
      {children && <div className="max-w-md text-xs leading-relaxed text-ink-3">{children}</div>}
    </div>
  )
}

export function Segmented<T extends string>({ value, options, onChange, size = 'md' }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; size?: 'sm' | 'md' }) {
  return (
    <div role="tablist" className="inline-flex rounded-xl bg-card-2 p-1 ring-1 ring-line">
      {options.map(o => (
        <button key={o.value} role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={clsx('rounded-lg font-medium transition-colors', size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-[13px]',
            value === o.value ? 'bg-card text-ink shadow-sm ring-1 ring-line-2' : 'text-ink-3 hover:text-ink-2')}>{o.label}</button>
      ))}
    </div>
  )
}

/** Honest data-freshness indicator. Never claims "live": data passes through Infloww sync delays plus our cache. */
export function DataStatus({ meta, className }: { meta?: Meta; className?: string }) {
  if (!meta) return null
  if (!meta.configured) return <Badge tone="bad" title="INFLOWW_API_KEY / INFLOWW_AGENCY_OID missing on the backend"><XCircle size={12} />Infloww not configured</Badge>
  const missing = Object.values(meta.coverage || {}).reduce((a, c) => a + (c.missing_days || 0), 0)
  const unavailable = Object.keys(meta.unavailable || {})
  return (
    <div className={clsx('flex flex-wrap items-center gap-1.5', className)}>
      {meta.complete ? <Badge tone="good" title={`Last synced ${ago(meta.newest_fetch)}. Completed past days are kept as fetched (oldest fetch ${ago(meta.oldest_fetch)}); recent days refresh every 15 minutes.${meta.syncing ? ' A background refresh is running; figures update when it finishes.' : ''} Infloww itself lags OnlyFans by 1–24h depending on the report.`}>
          {meta.syncing ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}Synced {ago(meta.newest_fetch)}{meta.syncing && ' · refreshing'}</Badge>
        : meta.syncing ? <Badge tone="info"><Loader2 size={12} className="animate-spin" />Syncing from Infloww…</Badge>
        : <Badge tone="warn" title="Some creator-days in this range have not been synced yet; totals are partial."><AlertTriangle size={12} />Partial · {missing} creator-days pending</Badge>}
      {unavailable.length > 0 && <Badge tone="bad" title={Object.values(meta.unavailable).join('\n')}>{unavailable.length} dataset{unavailable.length > 1 ? 's' : ''} unavailable</Badge>}
    </div>
  )
}

export function PageHeader({ title, subtitle, meta, actions, avatar }: { title: string; subtitle?: ReactNode; meta?: Meta; actions?: ReactNode; avatar?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 items-center gap-4">
        {avatar}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-[26px]">{title}</h1>
          {subtitle && <div className="mt-1 text-sm text-ink-2">{subtitle}</div>}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">{meta && <DataStatus meta={meta} />}{actions}</div>
    </div>
  )
}

export function Notes({ items, title = 'How to read this' }: { items: string[]; title?: string }) {
  if (!items?.length) return null
  return (
    <details className="group card px-4 py-3 text-xs text-ink-3">
      <summary className="cursor-pointer list-none font-medium text-ink-2 select-none"><Info size={12} className="mr-1.5 inline" />{title}</summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 leading-relaxed">{items.map((n, i) => <li key={i}>{n}</li>)}</ul>
    </details>
  )
}

export function SourceTag({ source }: { source: 'infloww' | 'estimate' | 'local' | 'derived' }) {
  const m = { infloww: ['Infloww', 'info'], estimate: ['Estimate', 'warn'], local: ['Local input', 'accent'], derived: ['Derived', 'neutral'] } as const
  return <Badge tone={m[source][1]}>{m[source][0]}</Badge>
}

export function RefreshButton({ onClick, busy }: { onClick: () => void; busy?: boolean }) {
  return <button onClick={onClick} className="btn" disabled={busy}><RefreshCw size={14} className={clsx(busy && 'animate-spin')} />Refresh</button>
}
