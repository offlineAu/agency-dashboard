import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useId, useState, type ReactNode } from 'react'
import { compact, money, num, shortDate } from '../lib/format'

// Validated categorical order: blue, orange, aqua, yellow, magenta, green, violet, red.
// CSS variables, so every chart follows the active theme (light/dark steps live in index.css).
export const SERIES = [1, 2, 3, 4, 5, 6, 7, 8].map(i => `var(--color-s${i})`)
const SURFACE = 'var(--color-card)'
// Fixed colour per revenue source so the same source keeps its colour on every chart.
export const TYPE_COLOR: Record<string, string> = {
  'Subscription': SERIES[0], 'Recurring Subscription': SERIES[6], 'Messages': SERIES[1], 'Posts': SERIES[3],
  'Tips': SERIES[2], 'Streams': SERIES[4], 'Referrals': SERIES[5], 'Unknown': 'var(--t-unknown)',
}

type Fmt = 'money' | 'num' | 'pct'
const fmtVal = (v: number | null | undefined, f: Fmt) => f === 'money' ? money(v) : f === 'pct' ? (v == null ? '—' : `${v.toFixed(1)}%`) : num(v)
const fmtAxis = (v: number, f: Fmt) => f === 'money' ? money(v, { compact: true }).replace('.00', '') : f === 'pct' ? `${v}%` : compact(v)

function TipBox({ title, rows }: { title: ReactNode; rows: { color: string; label: string; value: string }[] }) {
  return (
    <div className="min-w-44 rounded-xl border border-line bg-card px-3 py-2.5 text-xs shadow-xl">
      <div className="mb-1.5 font-semibold text-ink">{title}</div>
      {rows.map(r => (
        <div key={r.label} className="flex items-center justify-between gap-4 py-0.5">
          <span className="flex items-center gap-2 text-ink-2"><span className="inline-block size-2 rounded-full" style={{ background: r.color }} />{r.label}</span>
          <span className="font-semibold text-ink tabular">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

export interface SeriesDef { key: string; label: string; color: string }

/** Time series (area for one series, lines for several). Crosshair + one tooltip listing every series. */
export function TimeSeries({ data, series, x = 'bucket', fmt = 'money', height = 280, stacked = false, area = true, legend = true }: {
  data: any[]; series: SeriesDef[]; x?: string; fmt?: Fmt; height?: number; stacked?: boolean; area?: boolean; legend?: boolean
}) {
  const uid = useId().replace(/:/g, '')
  const tooltip = (
    <Tooltip cursor={{ stroke: 'var(--t-cursor)', strokeWidth: 1, strokeDasharray: '4 4' }} content={({ active, payload, label }) => active && payload?.length ? (
      <TipBox title={shortDate(String(label))} rows={series.map(s => ({ color: s.color, label: s.label, value: fmtVal(payload.find(p => p.dataKey === s.key)?.value as number, fmt) }))} />
    ) : null} />
  )
  // Recharts finds axes by direct child type, so these are rendered inline (not inside a fragment).
  const grid = <CartesianGrid vertical={false} strokeDasharray="4 4" />
  const xAxis = <XAxis dataKey={x} tickFormatter={v => shortDate(String(v))} tickLine={false} axisLine={false} minTickGap={24} dy={6} />
  const yAxis = <YAxis tickFormatter={v => fmtAxis(v, fmt)} tickLine={false} axisLine={false} width={56} />
  const dot = (c: string) => ({ r: 5, strokeWidth: 3, stroke: SURFACE, fill: c })
  return (
    <div>
      {legend && series.length > 1 && <div className="mb-3"><Legend items={series} /></div>}
      <div style={{ height }} role="img" aria-label={`Chart of ${series.map(s => s.label).join(', ')}`}>
        <ResponsiveContainer>
          {area ? (
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>{series.map(s => (
                <linearGradient key={s.key} id={`g-${uid}-${s.key.replace(/\W/g, '')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity={series.length > 1 ? 0.22 : 0.3} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0} />
                </linearGradient>))}
              </defs>
              {grid}{xAxis}{yAxis}{tooltip}
              {series.map(s => <Area key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2.5}
                fill={`url(#g-${uid}-${s.key.replace(/\W/g, '')})`} stackId={stacked ? 'a' : undefined} activeDot={dot(s.color)} isAnimationActive={false} />)}
            </AreaChart>
          ) : (
            <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              {grid}{xAxis}{yAxis}{tooltip}
              {series.map(s => <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2.5} dot={false}
                activeDot={dot(s.color)} isAnimationActive={false} />)}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/** Stacked bars over time (e.g. revenue by source per day/week/month). */
export function StackedBars({ data, series, x = 'bucket', fmt = 'money', height = 300 }: { data: any[]; series: SeriesDef[]; x?: string; fmt?: Fmt; height?: number }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="22%">
          <CartesianGrid vertical={false} strokeDasharray="4 4" />
          <XAxis dataKey={x} tickFormatter={v => shortDate(String(v))} tickLine={false} axisLine={false} minTickGap={20} dy={6} />
          <YAxis tickFormatter={v => fmtAxis(v, fmt)} tickLine={false} axisLine={false} width={56} />
          <Tooltip content={({ active, payload, label }) => active && payload?.length ? (
            <TipBox title={shortDate(String(label))} rows={[...series].reverse().filter(s => payload.find(p => p.dataKey === s.key)?.value).map(s => ({ color: s.color, label: s.label, value: fmtVal(payload.find(p => p.dataKey === s.key)?.value as number, fmt) }))} />
          ) : null} />
          {series.map((s, i) => <Bar key={s.key} dataKey={s.key} stackId="a" fill={s.color} stroke={SURFACE} strokeWidth={1}
            radius={i === series.length - 1 ? [5, 5, 0, 0] : 0} isAnimationActive={false} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Ranked horizontal bars with direct labels — the default for "who/what is biggest". */
export function BarList({ items, fmt = 'money', color = SERIES[0], max, onClick }: {
  items: { key: string; label: ReactNode; value: number | null; sub?: ReactNode; color?: string; lead?: ReactNode }[]; fmt?: Fmt; color?: string; max?: number; onClick?: (k: string) => void
}) {
  const m = max ?? Math.max(1, ...items.map(i => i.value || 0))
  return (
    <ul className="space-y-3">
      {items.map(i => (
        <li key={i.key}>
          <button type="button" disabled={!onClick} onClick={() => onClick?.(i.key)} className="group flex w-full items-center gap-3 text-left disabled:cursor-default">
            {i.lead}
            <span className="min-w-0 flex-1">
              <span className="mb-1.5 flex items-baseline justify-between gap-3 text-[13px]">
                <span className="truncate font-medium text-ink group-enabled:group-hover:text-accent">{i.label}</span>
                <span className="shrink-0 font-semibold tabular">{fmtVal(i.value, fmt)}{i.sub && <span className="ml-2 text-xs font-normal text-ink-3">{i.sub}</span>}</span>
              </span>
              <span className="block h-2 rounded-full" style={{ background: 'var(--t-track)' }}>
                <span className="block h-2 rounded-full transition-[width]" style={{ width: `${Math.max(0.5, ((i.value || 0) / m) * 100)}%`, background: i.color || color }} />
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

/** Part-to-whole as one segmented bar + legend list (more legible than a donut for 3–8 parts). */
export function ShareBar({ items, fmt = 'money' }: { items: { key: string; label: string; value: number; color: string }[]; fmt?: Fmt }) {
  const total = items.reduce((a, b) => a + (b.value || 0), 0)
  if (!total) return null
  return (
    <div>
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-full">
        {items.filter(i => i.value > 0).map(i => <div key={i.key} title={`${i.label}: ${fmtVal(i.value, fmt)}`} style={{ width: `${(i.value / total) * 100}%`, background: i.color }} />)}
      </div>
      <ShareLegend items={items} total={total} fmt={fmt} />
    </div>
  )
}

function ShareLegend({ items, total, fmt, cols = 2 }: { items: { key: string; label: string; value: number; color: string }[]; total: number; fmt: Fmt; cols?: 1 | 2 }) {
  return (
    <ul className={`mt-4 grid grid-cols-1 gap-x-6 gap-y-2.5 ${cols === 2 ? 'sm:grid-cols-2' : ''}`}>
      {items.map(i => (
        <li key={i.key} className="flex items-center justify-between gap-3 text-[13px]">
          <span className="flex min-w-0 items-center gap-2 text-ink-2"><span className="size-2.5 shrink-0 rounded-full" style={{ background: i.color }} /><span className="truncate">{i.label}</span></span>
          <span className="shrink-0 tabular"><span className="font-semibold">{fmtVal(i.value, fmt)}</span><span className="ml-2 inline-block w-11 text-right text-xs text-ink-3">{((i.value / total) * 100).toFixed(1)}%</span></span>
        </li>
      ))}
    </ul>
  )
}

/** Donut with the total in the centre and a value legend (identity never relies on colour alone). */
export function Donut({ items, fmt = 'money', centerLabel = 'Total', height = 200 }: {
  items: { key: string; label: string; value: number; color: string }[]; fmt?: Fmt; centerLabel?: string; height?: number
}) {
  const [hover, setHover] = useState<string | null>(null)
  const total = items.reduce((a, b) => a + (b.value || 0), 0)
  if (!total) return null
  const shown = items.filter(i => i.value > 0)
  const h = shown.find(i => i.key === hover)
  return (
    <div>
      <div className="relative mx-auto w-full max-w-[200px]" style={{ height }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={shown} dataKey="value" nameKey="label" innerRadius="70%" outerRadius="100%" paddingAngle={shown.length > 1 ? 2 : 0} cornerRadius={6}
              stroke={SURFACE} strokeWidth={2} isAnimationActive={false} onMouseEnter={(_, i) => setHover(shown[i].key)} onMouseLeave={() => setHover(null)}>
              {shown.map(i => <Cell key={i.key} fill={i.color} opacity={hover && hover !== i.key ? 0.35 : 1} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <div className="text-[11px] text-ink-3">{h ? h.label : centerLabel}</div>
            <div className="text-lg font-semibold tabular">{fmtVal(h ? h.value : total, fmt).replace(/\.00$/, '')}</div>
            {h && <div className="text-[11px] text-ink-3 tabular">{((h.value / total) * 100).toFixed(1)}%</div>}
          </div>
        </div>
      </div>
      <ShareLegend items={items} total={total} fmt={fmt} cols={1} />
    </div>
  )
}

/** Radial tick gauge for ONE proportion (0–100%). Value and label are always printed. */
export function Gauge({ value, label, sub, color = 'var(--color-accent)' }: { value: number | null; label: string; sub?: ReactNode; color?: string }) {
  const ticks = 40
  const v = value == null ? 0 : Math.max(0, Math.min(100, value))
  const on = Math.round((v / 100) * ticks)
  const cx = 120, cy = 118, r1 = 82, r2 = 104
  return (
    <div className="text-center" role="img" aria-label={`${label}: ${value == null ? 'no data' : v.toFixed(1) + '%'}`}>
      <svg viewBox="0 0 240 132" className="mx-auto w-full max-w-[280px]">
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const a = Math.PI - (i / ticks) * Math.PI
          const cos = Math.cos(a), sin = Math.sin(a)
          return <line key={i} x1={cx + r1 * cos} y1={cy - r1 * sin} x2={cx + r2 * cos} y2={cy - r2 * sin}
            stroke={i <= on && value != null ? color : 'var(--t-track)'} strokeWidth={4.5} strokeLinecap="round" />
        })}
        <text x={cx} y={cy - 8} textAnchor="middle" className="fill-ink" style={{ fontSize: 34, fontWeight: 600 }}>
          {value == null ? '—' : v.toFixed(1)}{value != null && <tspan className="fill-ink-3" style={{ fontSize: 16, fontWeight: 500 }} dx="2">%</tspan>}
        </text>
      </svg>
      <div className="-mt-1 text-[13px] font-medium text-ink">{label}</div>
      {sub && <div className="mt-0.5 text-xs text-ink-3">{sub}</div>}
    </div>
  )
}

/** Tiny trend line for a KPI card. Decorative context only: the KPI value and delta carry the numbers. */
export function Sparkline({ data, k, color = SERIES[0], height = 44, light = false }: { data: any[]; k: string; color?: string; height?: number; light?: boolean }) {
  const uid = useId().replace(/:/g, '')
  if (!data?.length || data.length < 2) return null
  return (
    <div style={{ height }} aria-hidden="true">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 4, right: 2, left: 2, bottom: 2 }}>
          <defs>
            <linearGradient id={`sp-${uid}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={light ? '#fff' : color} stopOpacity={light ? 0.35 : 0.28} />
              <stop offset="100%" stopColor={light ? '#fff' : color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis hide domain={['dataMin', 'dataMax']} />
          <Area type="monotone" dataKey={k} stroke={light ? '#fff' : color} strokeWidth={2} fill={`url(#sp-${uid})`} dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Simple vertical bars (single series) with soft gradient fill and per-bar tooltip. */
export function Bars({ data, x, y, fmt = 'money', height = 240, color = SERIES[0], labelFmt }: { data: any[]; x: string; y: string; fmt?: Fmt; height?: number; color?: string; labelFmt?: (v: any) => string }) {
  const uid = useId().replace(/:/g, '')
  const [active, setActive] = useState<number | null>(null)
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="28%" onMouseLeave={() => setActive(null)}
          onMouseMove={(s: any) => setActive(s?.activeTooltipIndex ?? null)}>
          <defs>
            <linearGradient id={`b-${uid}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.95} />
              <stop offset="100%" stopColor={color} stopOpacity={0.35} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="4 4" />
          <XAxis dataKey={x} tickFormatter={labelFmt || (v => String(v))} tickLine={false} axisLine={false} interval="preserveStartEnd" dy={6} />
          <YAxis tickFormatter={v => fmtAxis(v, fmt)} tickLine={false} axisLine={false} width={50} />
          <Tooltip cursor={false} content={({ active: a, payload, label }) => a && payload?.length ? (
            <TipBox title={labelFmt ? labelFmt(label) : String(label)} rows={[{ color, label: y, value: fmtVal(payload[0].value as number, fmt) }]} />) : null} />
          <Bar dataKey={y} radius={[6, 6, 0, 0]} isAnimationActive={false}>
            {data.map((_, i) => <Cell key={i} fill={active === i ? color : `url(#b-${uid})`} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function Legend({ items }: { items: SeriesDef[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map(s => <span key={s.key} className="inline-flex items-center gap-1.5"><span className="inline-block size-2 rounded-full" style={{ background: s.color }} />{s.label}</span>)}
    </div>
  )
}
