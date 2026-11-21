import { GitCompare } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarList } from '../components/charts'
import { DataTable, type Column } from '../components/DataTable'
import { Avatar } from '../components/Avatar'
import { Badge, Card, Delta, ErrorState, Kpi, Notes, PageHeader, PageSkeleton } from '../components/ui'
import { useFilters, useFilterSearch } from '../lib/filters'
import { money, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

export default function Creators() {
  const q = useDash('/creators')
  const f = useFilters()
  const search = useFilterSearch()
  const nav = useNavigate()
  const [sel, setSel] = useState<string[]>([])
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const rows: any[] = q.data.items
  const total = rows.reduce((a, r) => a + r.revenue, 0)
  const growing = rows.filter(r => (r.growth.value ?? 0) > 0).length
  const toggle = (id: string) => setSel(s => s.includes(id) ? s.filter(x => x !== id) : s.length >= 6 ? s : [...s, id])
  const compareSearch = () => { const p = new URLSearchParams(search.slice(1)); p.set('ids', sel.join(',')); return `?${p}` }

  const cols: Column<any>[] = [
    { key: 'pick', label: '', sortable: false, render: r => <input type="checkbox" aria-label={`Select ${r.name} for comparison`} checked={sel.includes(r.id)} onClick={e => e.stopPropagation()} onChange={() => toggle(r.id)} className="accent-[#7c5cff]" /> },
    { key: 'name', label: 'Creator', render: r => <div className="flex items-center gap-2.5"><Avatar kind="creator" id={r.id} name={r.name} size={34} /><div className="min-w-0"><div className="font-medium">{r.name || r.id}</div><div className="text-[11px] text-ink-3">@{r.user_name || '—'} · ID {r.id}</div></div></div> },
    { key: 'status', label: 'Status', hideBelow: 'md', render: r => <Badge tone={r.connected ? 'good' : 'warn'}>{r.status || (r.connected ? 'connected' : 'unknown')}</Badge> },
    { key: 'revenue', label: f.basis === 'net' ? 'Net revenue' : 'Gross revenue', align: 'right', render: r => <span className="font-semibold">{money(r.revenue)}</span> },
    { key: 'growth', label: 'Growth', align: 'right', value: r => r.growth.value, render: r => <Delta g={r.growth} /> },
    { key: 'share_of_agency', label: 'Share', align: 'right', hideBelow: 'lg', render: r => pct(r.share_of_agency) },
    { key: 'subscription_revenue', label: 'Subs', align: 'right', hideBelow: 'lg', render: r => money(r.subscription_revenue, { compact: true }) },
    { key: 'ppv_revenue', label: 'PPV', align: 'right', hideBelow: 'lg', render: r => money(r.ppv_revenue, { compact: true }) },
    { key: 'tips', label: 'Tips', align: 'right', hideBelow: 'lg', render: r => money(r.tips, { compact: true }) },
    { key: 'refunds', label: 'Refunds', align: 'right', hideBelow: 'lg', render: r => r.refunds ? <span className="text-bad">{money(r.refunds, { compact: true })}</span> : money(0) },
    { key: 'active_fans', label: 'Active fans', align: 'right', hideBelow: 'md', render: r => num(r.active_fans) },
    { key: 'new_subscribers', label: 'New subs', align: 'right', hideBelow: 'md', render: r => num(r.new_subscribers) },
    { key: 'expired_fans', label: 'Expired', align: 'right', hideBelow: 'lg', render: r => num(r.expired_fans) },
    { key: 'auto_renew_pct', label: 'Auto-renew', align: 'right', hideBelow: 'md', title: 'Fans with auto-renew on ÷ active fans (latest day)', render: r => pct(r.auto_renew_pct) },
    { key: 'avg_revenue_per_paying_fan', label: '$ / paying fan', align: 'right', hideBelow: 'lg', render: r => money(r.avg_revenue_per_paying_fan) },
  ]

  return (
    <div>
      <PageHeader title="Creators" subtitle="Performance, growth and audience health for every connected creator." meta={q.data.meta}
        actions={sel.length >= 2 ? <button className="btn-primary" onClick={() => nav(`/creators/compare${compareSearch()}`)}><GitCompare size={14} />Compare {sel.length}</button>
          : <span className="text-xs text-ink-3">Tick 2–6 creators to compare</span>} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Connected creators" value={num(rows.filter(r => r.connected).length)} sub={<span>{rows.filter(r => r.revenue > 0).length} earned in range</span>} />
        <Kpi label="Total revenue" value={money(total)} sub={<span>{f.basis}</span>} />
        <Kpi label="Growing creators" value={`${growing}/${rows.length}`} sub={<span>vs previous period</span>} />
        <Kpi label="Avg revenue / creator" value={money(rows.length ? total / rows.length : null)} />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Creator directory" subtitle="Click a row for the full creator profile">
          <DataTable rows={rows} columns={cols} rowKey={r => r.id} initialSort={{ key: 'revenue', dir: 'desc' }} searchable searchPlaceholder="Search creators…"
            onRowClick={r => nav(`/creators/${r.id}${search}`)} />
        </Card>
        <Card title="Revenue leaderboard" subtitle="Ranked by revenue in range">
          <BarList onClick={id => nav(`/creators/${id}${search}`)} items={rows.slice(0, 10).map(r => ({ key: r.id, label: r.name, value: r.revenue, sub: pct(r.share_of_agency, 0), lead: <Avatar kind="creator" id={r.id} name={r.name} size={30} /> }))} />
        </Card>
      </div>
      <div className="mt-4"><Notes items={[
        'Revenue = Infloww transactions with status done/loading in the selected UTC range. Growth compares with the previous period of equal length.',
        'Active fans, expired fans and auto-renew are the latest reported day in range (Infloww creator reports, up to 24h delayed). New subs are summed.',
        'Refunds are dated by refund time. "$ / paying fan" = revenue ÷ distinct fans with a recognised transaction in range.',
        'Only creators included in the API key\'s scope are visible. New or relinked creators must be added to the key in Infloww.',
      ]} /></div>
    </div>
  )
}
