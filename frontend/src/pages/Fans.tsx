import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { useState } from 'react'
import { BarList, Bars, SERIES, TimeSeries } from '../components/charts'
import { Badge, Card, Empty, ErrorState, InfoTip, Kpi, Notes, PageHeader, PageSkeleton, Segmented } from '../components/ui'
import { apiGet } from '../lib/api'
import { useFilters } from '../lib/filters'
import { money, num, pct, shortDate } from '../lib/format'
import { useDash } from '../lib/hooks'

const SEG_TONE: Record<string, any> = { VIP: 'accent', 'High Value': 'info', Regular: 'neutral', 'Non-spender': 'warn' }
const SEG_COLOR: Record<string, string> = { VIP: SERIES[6], 'High Value': SERIES[0], Regular: SERIES[2], 'Non-spender': SERIES[3] }

export default function Fans() {
  const f = useFilters()
  const q = useDash('/fans')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('lifetime')
  const [segment, setSegment] = useState('')
  const [search, setSearch] = useState('')
  const top = useQuery({
    queryKey: ['top', f.params, page, sort, segment, search],
    queryFn: () => apiGet('/fans/top-spenders', { ...f.params, page, page_size: 20, sort, segment, search }),
    placeholderData: keepPreviousData,
  })
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const aud = d.audience
  const t = d.totals || {}
  const th = d.thresholds
  const pages = top.data ? Math.max(1, Math.ceil(top.data.total / 20)) : 1

  return (
    <div>
      <PageHeader title="Fan intelligence" subtitle="Audience health from creator reports, and spending behaviour from transactions." meta={d.meta} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Active fans" value={num(aud.active_fans)} unavailable={aud.active_fans == null ? 'No creator report data' : undefined} sub={<span>{num(aud.expired_fans)} expired · latest day</span>} />
        <Kpi label="New subscribers" value={num(aud.new_subscribers)} sub={<span>{num(aud.renewals)} renewals in range</span>} />
        <Kpi label="Auto-renew on" value={pct(aud.auto_renew_pct)} sub={<span>{num(aud.fans_with_renew_on)} fans</span>} />
        <Kpi label="Paying fans in range" value={num(t.paying_fans_in_period)} unavailable={!d.available ? d.reason : undefined}
          sub={<span>{num(t.new_paying_fans_in_period)} new · {num(t.returning_paying_fans_in_period)} returning</span>}
          tip="Distinct fans with at least one recognised transaction in range. 'Returning' = first seen before the range start (within synced history)." />
      </div>
      {d.available && (
        <div className="mt-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Kpi label="Avg lifetime value" value={money(t.avg_ltv)} tip={`Average spend per paying fan since ${d.history.start} (synced history; API retains ~1 year).`} sub={<span>{num(t.known_paying_fans)} known paying fans</span>} />
          <Kpi label="Avg spend in range" value={money(t.avg_spend_in_period)} />
          <Kpi label="Purchases / fan" value={num(t.avg_purchases_per_fan, 1)} sub={<span>over synced history</span>} />
          <Kpi label="PPV buyers" value={num(t.ppv_buyers)} sub={<span>{pct(t.known_paying_fans ? t.ppv_buyers / t.known_paying_fans * 100 : null)} of paying fans</span>} />
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Subscriber trend" subtitle="Daily active & expired fans (sum across creators)">
          {aud.trend.length ? <TimeSeries data={aud.trend} x="day" fmt="num" area={false} height={240} series={[{ key: 'activeFans', label: 'Active fans', color: SERIES[0] }, { key: 'expiredFans', label: 'Expired fans', color: SERIES[1] }]} />
            : <Empty title="No creator report data in range" />}
        </Card>
        <Card title="Fan segments" subtitle={<span className="inline-flex items-center gap-1">By spend over synced history <InfoTip text={`VIP ≥ ${money(th.vip_cents)}; High Value ≥ ${money(th.high_value_cents)}; Regular = any PPV/tip/other purchase below that; Non-spender = only subscription payments recorded. Change thresholds in Settings.`} /></span>}>
          {d.available ? (
            <div className="space-y-4">
              <BarList fmt="num" items={d.segments.map((s: any) => ({ key: s.segment, label: s.segment, value: s.fans, color: SEG_COLOR[s.segment], sub: money(s.lifetime, { compact: true }) }))} />
              <div className="flex flex-wrap gap-2 border-t border-line pt-3">
                {d.lifecycle.map((l: any) => <Badge key={l.lifecycle} tone={l.lifecycle === 'At Risk' ? 'bad' : l.lifecycle === 'New' ? 'good' : 'neutral'}>{l.lifecycle}: {num(l.fans)}</Badge>)}
              </div>
            </div>
          ) : <Empty title={d.reason} />}
        </Card>
      </div>

      {d.available && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Card title="Spending distribution" subtitle="Paying fans by spend over synced history">
            <Bars data={d.distribution.map((b: any) => ({ ...b, label: b.max ? `${money(b.min, { compact: true })}–${money(b.max, { compact: true })}` : `${money(b.min, { compact: true })}+` }))} x="label" y="fans" fmt="num" height={220} color={SERIES[6]} />
          </Card>
          <Card title="New paying fans" subtitle="First recorded purchase per day (after history start)">
            {d.acquisition.length ? <Bars data={d.acquisition} x="day" y="fans" fmt="num" height={220} color={SERIES[2]} labelFmt={v => shortDate(String(v))} /> : <Empty title="No first purchases in range" />}
          </Card>
        </div>
      )}

      {d.available && (
        <Card className="mt-4" title="Spending by creator" subtitle="Paying fans and spend in range">
          <BarList items={d.by_creator.map((c: any) => ({ key: c.creator_id, label: c.name || c.creator_id, value: c.spend, sub: `${num(c.fans)} fans` }))} />
        </Card>
      )}

      <Card className="mt-4" title="Top spenders" subtitle="Pseudonymised. Server-side paginated — the full fan list is never sent to the browser."
        action={<Segmented size="sm" value={sort} onChange={v => { setSort(v); setPage(1) }} options={[{ value: 'lifetime', label: 'Lifetime' }, { value: 'period_spend', label: 'In range' }, { value: 'purchases', label: 'Purchases' }]} />}>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative w-full max-w-xs"><Search size={14} className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-3" />
            <input className="input w-full pl-8" placeholder="Search fan ref…" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} aria-label="Search fans" /></div>
          <select className="input" value={segment} onChange={e => { setSegment(e.target.value); setPage(1) }} aria-label="Filter by segment">
            <option value="">All segments</option>{['VIP', 'High Value', 'Regular', 'Non-spender', 'New', 'Active', 'At Risk', 'Lapsed'].map(s => <option key={s}>{s}</option>)}
          </select>
          <span className="text-xs text-ink-3 tabular">{num(top.data?.total)} fans</span>
        </div>
        {!top.data?.available ? <Empty title={top.data?.reason || 'Loading…'} /> : (
          <div className={`-mx-5 overflow-x-auto px-5 ${top.isFetching ? 'opacity-60' : ''}`}>
            <table className="w-full text-[13px]">
              <thead><tr className="text-[11px] text-ink-3 uppercase">{['Fan', 'Segment', 'Lifetime', 'In range', 'Purchases', 'PPV buys', 'Tips', 'Last purchase', 'Creators'].map((h, i) =>
                <th key={h} className={`border-b border-line py-2 font-medium ${i > 1 ? 'px-3 text-right' : 'pr-3 text-left'} ${i >= 5 ? 'hidden md:table-cell' : ''}`}>{h}</th>)}</tr></thead>
              <tbody>{top.data.items.map((r: any) => (
                <tr key={r.fan_ref} className="border-b border-line/60">
                  <td className="py-2 pr-3">{r.fan_name || '—'} <span className="text-[11px] text-ink-3">{r.fan_ref}</span></td>
                  <td className="pr-3"><Badge tone={SEG_TONE[r.segment]}>{r.segment}</Badge>{r.lifecycle && <span className="ml-1 text-[11px] text-ink-3">{r.lifecycle}</span>}</td>
                  <td className="px-3 text-right font-semibold tabular">{money(r.lifetime)}</td>
                  <td className="px-3 text-right tabular">{money(r.period_spend)}</td>
                  <td className="px-3 text-right tabular">{num(r.purchases)}</td>
                  <td className="hidden px-3 text-right tabular md:table-cell">{num(r.ppv_purchases)}</td>
                  <td className="hidden px-3 text-right tabular md:table-cell">{money(r.tips)}</td>
                  <td className="hidden px-3 text-right tabular md:table-cell">{shortDate(r.last_day)}</td>
                  <td className="hidden px-3 text-right tabular md:table-cell">{r.creators}</td>
                </tr>))}</tbody>
            </table>
            {!top.data.items.length && <Empty title="No fans match" />}
          </div>
        )}
        <div className="mt-3 flex items-center justify-end gap-2 text-xs text-ink-3">
          <span className="tabular">Page {page} of {pages}</span>
          <button className="btn-icon" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft size={14} /></button>
          <button className="btn-icon" aria-label="Next page" disabled={page >= pages} onClick={() => setPage(page + 1)}><ChevronRight size={14} /></button>
        </div>
      </Card>
      <div className="mt-4"><Notes items={d.limitations || []} title="Data rules & limitations" /></div>
    </div>
  )
}
