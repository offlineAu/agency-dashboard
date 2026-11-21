import { ArrowLeft } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Legend, SERIES, TimeSeries } from '../components/charts'
import { Card, Delta, Empty, ErrorState, PageHeader, PageSkeleton } from '../components/ui'
import { useFilterSearch } from '../lib/filters'
import { money, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

const ROWS: [string, string, (r: any) => any, ('max' | 'min')?][] = [
  ['Revenue', 'revenue', r => money(r.revenue), 'max'],
  ['Growth vs previous', 'growth', r => <Delta g={r.growth} />],
  ['Share of agency', 'share_of_agency', r => pct(r.share_of_agency), 'max'],
  ['Subscriptions', 'subscription_revenue', r => money(r.subscription_revenue), 'max'],
  ['PPV', 'ppv_revenue', r => money(r.ppv_revenue), 'max'],
  ['Tips', 'tips', r => money(r.tips), 'max'],
  ['Refunds', 'refunds', r => money(r.refunds), 'min'],
  ['Paying fans', 'paying_fans', r => num(r.paying_fans), 'max'],
  ['Revenue / paying fan', 'avg_revenue_per_paying_fan', r => money(r.avg_revenue_per_paying_fan), 'max'],
  ['Active fans (latest)', 'active_fans', r => num(r.active_fans), 'max'],
  ['New subscribers', 'new_subscribers', r => num(r.new_subscribers), 'max'],
  ['Renewals', 'renewals', r => num(r.renewals), 'max'],
  ['Expired fans (latest)', 'expired_fans', r => num(r.expired_fans), 'min'],
  ['Auto-renew on', 'auto_renew_pct', r => pct(r.auto_renew_pct), 'max'],
  ['Avg subscription length', 'avg_subscription_length_days', r => r.avg_subscription_length_days == null ? '—' : `${num(r.avg_subscription_length_days)} d`, 'max'],
  ['Profile visitors', 'profile_visitors', r => num(r.profile_visitors), 'max'],
]

export default function CreatorCompare() {
  const [sp] = useSearchParams()
  const ids = sp.get('ids') || ''
  const search = useFilterSearch()
  const q = useDash('/creators/compare', { ids }, { enabled: ids.split(',').length >= 2 })
  if (ids.split(',').filter(Boolean).length < 2) return <Card><Empty title="Pick at least two creators">Select creators on the <Link className="link" to={`/creators${search}`}>Creators</Link> page.</Empty></Card>
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const items: any[] = q.data.items
  const series = items.map((c, i) => ({ key: c.id, label: c.name || c.id, color: SERIES[i] }))
  const merged: Record<string, any> = {}
  for (const c of items) for (const p of q.data.trends[c.id] || []) { (merged[p.bucket] ||= { bucket: p.bucket })[c.id] = p.value }
  const data = Object.values(merged).sort((a: any, b: any) => a.bucket.localeCompare(b.bucket))

  return (
    <div>
      <Link to={`/creators${search}`} className="mb-3 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink-2"><ArrowLeft size={13} />All creators</Link>
      <PageHeader title="Creator comparison" subtitle={`${items.length} creators side by side`} meta={q.data.meta} />
      <Card title="Revenue trend" action={<Legend items={series} />}>
        <TimeSeries data={data} series={series} area={false} legend={false} />
      </Card>
      <Card className="mt-4" title="Metrics" subtitle="Best value per row highlighted">
        <div className="-mx-5 overflow-x-auto px-5">
          <table className="w-full text-[13px]">
            <thead><tr><th className="py-2 pr-3 text-left text-[11px] font-medium text-ink-3 uppercase">Metric</th>
              {items.map((c, i) => <th key={c.id} className="px-3 py-2 text-right text-[12px] font-semibold whitespace-nowrap"><span className="mr-1.5 inline-block h-0.5 w-3 rounded align-middle" style={{ background: SERIES[i] }} /><Link className="hover:underline" to={`/creators/${c.id}${search}`}>{c.name}</Link></th>)}</tr></thead>
            <tbody>
              {ROWS.map(([label, key, fmt, best]) => {
                const vals = items.map(c => c[key]).filter((v: any) => typeof v === 'number')
                const target = best === 'max' ? Math.max(...vals) : best === 'min' ? Math.min(...vals) : null
                return (
                  <tr key={key} className="border-t border-line/60">
                    <td className="py-2 pr-3 text-ink-2">{label}</td>
                    {items.map(c => <td key={c.id} className={`px-3 py-2 text-right tabular ${target !== null && vals.length > 1 && c[key] === target ? 'font-semibold text-good' : ''}`}>{fmt(c)}</td>)}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
