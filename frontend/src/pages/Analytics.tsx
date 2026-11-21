import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { BarList } from '../components/charts'
import { DataTable } from '../components/DataTable'
import { Badge, Card, Empty, ErrorState, Kpi, PageHeader, PageSkeleton } from '../components/ui'
import { apiGet } from '../lib/api'
import { money, msDate, num, pct } from '../lib/format'
import { useDash, useMeta } from '../lib/hooks'

function Scripts() {
  const meta = useMeta()
  const creators = (meta.data?.creators || []).filter((c: any) => c.connected)
  const [cid, setCid] = useState('')
  const id = cid || creators[0]?.id
  const q = useQuery({ queryKey: ['scripts', id], queryFn: () => apiGet(`/creators/${id}/scripts`), enabled: !!id, staleTime: 10 * 60_000 })
  const rows = (k: 'tags' | 'sequences') => (q.data?.[k] || []).map((r: any) => ({ ...r, rate: r.send_count ? (r.purchases || 0) / r.send_count * 100 : null }))
  const cols = [
    { key: 'name', label: 'Name' }, { key: 'send_count', label: 'Sends', align: 'right' as const, render: (r: any) => num(r.send_count) },
    { key: 'purchases', label: 'Purchases', align: 'right' as const, render: (r: any) => num(r.purchases) },
    { key: 'rate', label: 'Purchase rate', align: 'right' as const, render: (r: any) => pct(r.rate) },
    { key: 'revenue', label: 'Revenue', align: 'right' as const, render: (r: any) => <b>{money(r.revenue)}</b> },
  ]
  return (
    <Card className="mt-4" title="Script performance" subtitle="Cumulative statistics per script tag and sequence (all-time, fetched live)"
      action={<select className="input" value={id || ''} onChange={e => setCid(e.target.value)} aria-label="Creator">{creators.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>}>
      {!id ? <Empty title="No creators" /> : q.isLoading ? <div className="skeleton h-32" /> : !q.data?.available ? <Empty title="Script data unavailable">{q.data?.error?.message}</Empty> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div><div className="mb-2 text-xs font-medium text-ink-2">By tag</div><DataTable rows={rows('tags')} rowKey={r => 't' + r.id} columns={cols} pageSize={8} initialSort={{ key: 'revenue', dir: 'desc' }} dense /></div>
          <div><div className="mb-2 text-xs font-medium text-ink-2">By sequence</div><DataTable rows={rows('sequences')} rowKey={r => 's' + r.id} columns={cols} pageSize={8} initialSort={{ key: 'revenue', dir: 'desc' }} dense /></div>
        </div>
      )}
    </Card>
  )
}

export default function Analytics() {
  const q = useDash('/messages')
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const k = Object.fromEntries(d.by_kind.map((x: any) => [x.kind, x]))
  const label = (x: string) => x === 'automated' ? 'Automated' : 'Priority mass'
  return (
    <div>
      <PageHeader title="Message analytics" subtitle="Automated and priority mass messages: reach, conversion and revenue." meta={d.meta} />
      {d.errors?.length > 0 && <div className="mb-4 rounded-xl border border-warn/30 bg-warn/5 p-3 text-xs text-warn">Some message data failed to sync: {d.errors[0].message}</div>}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {['automated', 'priority_mass'].map(kind => (
          <Kpi key={kind} label={`${label(kind)} revenue`} value={money(k[kind]?.revenue)} sub={<span>{num(k[kind]?.n)} messages · {num(k[kind]?.sent)} sends</span>} />
        ))}
        {['automated', 'priority_mass'].map(kind => (
          <Kpi key={kind + 'r'} label={`${label(kind)} purchase rate`} value={pct(k[kind]?.purchase_rate, 2)} sub={<span>{money(k[kind]?.revenue_per_send)} per send</span>} />
        ))}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Revenue by configuring employee">{d.by_employee.length ? <BarList items={d.by_employee.slice(0, 8).map((e: any) => ({ key: String(e.employee_id), label: e.name || `Employee ${e.employee_id}`, value: e.revenue, sub: `${num(e.n)} msgs` }))} /> : <Empty title="No messages in range" />}</Card>
        <Card className="lg:col-span-2" title="Top messages" subtitle="By revenue, messages sent in range">
          <DataTable rows={d.items} rowKey={r => r.kind + r.id} pageSize={8} initialSort={{ key: 'revenue', dir: 'desc' }} empty={<Empty title="No messages in range" />} columns={[
            { key: 'preview', label: 'Message', render: r => <div className="max-w-72"><div className="truncate">{r.preview || <span className="text-ink-3">(media only)</span>}</div><div className="text-[11px] text-ink-3">{label(r.kind)} · {r.creator_name} · {msDate(r.sent_ms)}</div></div> },
            { key: 'status', label: 'Status', hideBelow: 'md', render: r => <Badge tone={r.status === 'Completed' ? 'good' : r.status === 'Canceled' ? 'bad' : 'neutral'}>{r.status}</Badge> },
            { key: 'times_sent', label: 'Sent', align: 'right', render: r => num(r.times_sent) },
            { key: 'purchases', label: 'Buys', align: 'right', render: r => num(r.purchases) },
            { key: 'purchase_rate', label: 'Rate', align: 'right', hideBelow: 'md', render: r => pct(r.purchase_rate, 1) },
            { key: 'revenue', label: 'Revenue', align: 'right', render: r => <b>{money(r.revenue)}</b> },
          ]} />
        </Card>
      </div>
      <Scripts />
    </div>
  )
}
