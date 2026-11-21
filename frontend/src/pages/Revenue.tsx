import clsx from 'clsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BarList, Legend, StackedBars, TYPE_COLOR } from '../components/charts'
import { Card, Delta, ErrorState, Kpi, Notes, PageHeader, PageSkeleton, Segmented, SourceTag } from '../components/ui'
import { useFilters, useFilterSearch } from '../lib/filters'
import { money, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

const ORDER = ['Subscription', 'Recurring Subscription', 'Messages', 'Posts', 'Tips', 'Streams', 'Referrals', 'Unknown']
const LABEL: Record<string, string> = { Subscription: 'New subscriptions', 'Recurring Subscription': 'Recurring subscriptions', Messages: 'PPV messages', Posts: 'PPV posts', Tips: 'Tips', Streams: 'Live streams', Referrals: 'Referrals', Unknown: 'Unknown' }

export default function Revenue() {
  const f = useFilters()
  const search = useFilterSearch()
  const [gran, setGran] = useState<'day' | 'week' | 'month'>('day')
  const fin = useDash('/finance')
  const rev = useDash('/dashboard/revenue', { granularity: gran })
  if (fin.isLoading || rev.isLoading) return <PageSkeleton />
  if (fin.error || rev.error) return <ErrorState error={fin.error || rev.error} onRetry={() => { fin.refetch(); rev.refetch() }} />
  const d = fin.data
  const cur = d.totals.current
  const g = d.totals.growth
  const present = ORDER.filter(t => rev.data.trend.some((r: any) => r[t]))
  const series = present.map(t => ({ key: t, label: LABEL[t], color: TYPE_COLOR[t] }))

  return (
    <div>
      <PageHeader title="Revenue & financials" subtitle="Infloww-reported revenue, separated from estimates that rely on your own business rules." meta={d.meta} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Gross revenue" value={money(cur.gross)} delta={<Delta g={g.gross} label="vs prev." />} sub={<span>{money(cur.gross_pending_clearance, { compact: true })} not yet cleared</span>} />
        <Kpi label="Net revenue" value={money(cur.net)} delta={<Delta g={g.net} />} sub={<span>platform fees {pct(d.fee_rate)}</span>} />
        <Kpi label="Refunds" value={money(cur.refunds)} sub={<span>{cur.refund_count} refunds · {pct(d.refund_rate)} of gross</span>} delta={<Delta g={g.refunds} invert />} />
        <Kpi label="Reversed / pending return" value={money(cur.reversed + cur.pending_return)} sub={<span>undo {money(cur.reversed, { compact: true })} · pending {money(cur.pending_return, { compact: true })}</span>} />
      </div>

      <Card className="mt-4" title="Revenue by source over time" subtitle={`${f.basis === 'net' ? 'Net' : 'Gross'} revenue, stacked by transaction type`}
        action={<Segmented size="sm" value={gran} onChange={setGran} options={[{ value: 'day', label: 'Daily' }, { value: 'week', label: 'Weekly' }, { value: 'month', label: 'Monthly' }]} />}>
        <div className="mb-3"><Legend items={series} /></div>
        <div className={rev.isFetching ? 'opacity-60' : ''}><StackedBars data={rev.data.trend} series={series} height={300} /></div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Profit & loss view" subtitle="Reported figures vs. estimates. Gross revenue is not agency profit.">
          <table className="w-full text-[13px]">
            <tbody>
              {d.reported.map((r: any) => (
                <tr key={r.key} className="border-b border-line/60">
                  <td className={clsx('py-2 pr-3', r.info ? 'pl-4 text-ink-3' : 'text-ink-2', ['gross', 'net'].includes(r.key) && 'font-semibold text-ink')}>{r.label}</td>
                  <td className="py-2"><SourceTag source="infloww" /></td>
                  <td className={clsx('py-2 text-right tabular', r.value < 0 && !r.info && 'text-bad', ['gross', 'net'].includes(r.key) && 'font-semibold')}>{r.value == null ? '—' : money(r.value)}</td>
                </tr>
              ))}
              <tr><td colSpan={3} className="pt-4 pb-1 text-[11px] font-medium tracking-wide text-ink-3 uppercase">Estimates (configured in Settings)</td></tr>
              {d.estimates.map((r: any) => (
                <tr key={r.key} className="border-b border-line/60">
                  <td className={clsx('py-2 pr-3', r.key === 'operating_profit' ? 'font-semibold text-ink' : 'text-ink-2')}>{r.label}{r.missing && <div className="text-[11px] text-ink-3">{r.missing}</div>}</td>
                  <td className="py-2"><SourceTag source={r.source} /></td>
                  <td className={clsx('py-2 text-right tabular', r.value < 0 && 'text-bad', r.key === 'operating_profit' && 'font-semibold')}>{r.value == null ? '—' : money(r.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 text-xs text-ink-3">Set commission & cost rules in <Link className="link" to={`/settings${search}`}>Settings</Link>.{d.undated_campaign_costs > 0 && ` ${d.undated_campaign_costs} campaign cost(s) have no spend date and are excluded from period totals.`}</div>
        </Card>
        <div className="space-y-4 lg:col-span-2">
          <Card title="Source breakdown" subtitle="Gross / net by type">
            <table className="w-full text-[13px]"><thead><tr className="text-[11px] text-ink-3 uppercase"><th className="pb-2 text-left font-medium">Source</th><th className="pb-2 text-right font-medium">Gross</th><th className="pb-2 text-right font-medium">Net</th><th className="pb-2 text-right font-medium">Share</th></tr></thead>
              <tbody>{d.breakdown.map((b: any) => <tr key={b.type} className="border-t border-line/60"><td className="py-1.5"><span className="mr-2 inline-block size-2 rounded-sm" style={{ background: TYPE_COLOR[b.type] }} />{b.label}</td><td className="text-right tabular">{money(b.gross)}</td><td className="text-right tabular">{money(b.net)}</td><td className="text-right text-ink-3 tabular">{pct(b.share)}</td></tr>)}</tbody>
            </table>
          </Card>
          <Card title="Revenue contribution by creator">
            <BarList items={rev.data.by_creator.slice(0, 8).map((c: any) => ({ key: c.creator_id, label: c.name || c.creator_id, value: c.value }))} />
          </Card>
        </div>
      </div>
      {d.invoices.length > 0 && (
        <Card className="mt-4" title="Infloww invoices" subtitle="Monthly billing from /v1/invoice-data/monthly-billing">
          <table className="w-full text-[13px]"><thead><tr className="text-[11px] text-ink-3 uppercase">{['Period', 'Subscription', 'Discount', 'Tax', 'Total', 'Paid', 'Pending'].map((h, i) => <th key={h} className={`pb-2 font-medium ${i ? 'text-right' : 'text-left'}`}>{h}</th>)}</tr></thead>
            <tbody>{d.invoices.map((i: any) => <tr key={i.billing_id} className="border-t border-line/60">{[i.period, money(i.subscription), money(i.discount), money(i.tax), money(i.total), money(i.paid), money(i.pending)].map((v, k) => <td key={k} className={`py-1.5 tabular ${k ? 'text-right' : ''}`}>{v}</td>)}</tr>)}</tbody></table>
        </Card>
      )}
      <div className="mt-4"><Notes items={[...d.notes,
        "Recognised revenue = status 'done' (cleared) + 'loading' (earned, not yet cleared on OnlyFans). 'undo' and 'pending_return' are shown separately and excluded.",
        'Net = Infloww net amount (after OnlyFans platform fee).']} /></div>
    </div>
  )
}
