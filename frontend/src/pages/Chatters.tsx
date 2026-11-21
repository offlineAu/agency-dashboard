import { useNavigate } from 'react-router-dom'
import { BarList, SERIES, TimeSeries } from '../components/charts'
import { DataTable, type Column } from '../components/DataTable'
import { Avatar } from '../components/Avatar'
import { Badge, Card, Delta, Empty, ErrorState, Kpi, Notes, PageHeader, PageSkeleton } from '../components/ui'
import { useFilterSearch } from '../lib/filters'
import { duration, money, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

const RULE_COLOR: Record<string, string> = { 'Message sender': SERIES[0], 'Last chatter': SERIES[2], 'Employee on shift': SERIES[6], 'Manually reassigned': SERIES[3], Unassigned: '#5b6380', '(none)': '#5b6380' }

export default function Chatters() {
  const q = useDash('/employees')
  const m = useDash('/employees/matrix')
  const search = useFilterSearch()
  const nav = useNavigate()
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const rows: any[] = q.data.items
  const att = q.data.attribution
  const totalSales = rows.reduce((a, r) => a + (r.sales || 0), 0)
  const msgs = rows.reduce((a, r) => a + (r.messages_sent || 0), 0)
  const ppvs = rows.reduce((a, r) => a + (r.ppvs_sent || 0), 0)
  const unlocked = rows.reduce((a, r) => a + (r.ppvs_unlocked || 0), 0)

  const cols: Column<any>[] = [
    { key: 'rank', label: '#', align: 'center', render: r => <span className="text-ink-3">{r.rank}</span> },
    { key: 'name', label: 'Chatter', render: r => <div className="flex items-center gap-2.5"><Avatar kind="employee" id={r.employee_id} name={r.name} size={34} /><div className="min-w-0"><div className="font-medium">{r.name}</div><div className="text-[11px] text-ink-3">{r.assigned_creators.length} creators · ID {r.employee_id}</div></div></div> },
    { key: 'status', label: 'Status', hideBelow: 'lg', render: r => <Badge tone={r.status === 'Activated' ? 'good' : 'neutral'}>{r.status}</Badge> },
    { key: 'sales', label: 'Attributed sales', align: 'right', render: r => <b>{money(r.sales)}</b> },
    { key: 'growth', label: 'Growth', align: 'right', value: r => r.growth.value, render: r => <Delta g={r.growth} /> },
    { key: 'ppv_sales', label: 'PPV', align: 'right', hideBelow: 'md', render: r => money(r.ppv_sales, { compact: true }) },
    { key: 'tips_sales', label: 'Tips', align: 'right', hideBelow: 'lg', render: r => money(r.tips_sales, { compact: true }) },
    { key: 'messages_sent', label: 'Msgs sent', align: 'right', hideBelow: 'md', render: r => num(r.messages_sent) },
    { key: 'ppvs_sent', label: 'PPVs sent', align: 'right', hideBelow: 'lg', render: r => num(r.ppvs_sent) },
    { key: 'unlock_rate', label: 'Unlock rate', align: 'right', hideBelow: 'md', title: 'PPVs unlocked ÷ PPVs sent (direct messages)', render: r => pct(r.unlock_rate) },
    { key: 'golden_ratio', label: 'Golden ratio', align: 'right', hideBelow: 'lg', title: 'PPVs sent ÷ messages sent', render: r => pct(r.golden_ratio) },
    { key: 'sales_per_message', label: '$ / msg', align: 'right', hideBelow: 'lg', render: r => money(r.sales_per_message) },
    { key: 'avg_response_clocked_ms', label: 'Avg reply', align: 'right', hideBelow: 'md', title: 'Average reply time during clocked hours (message-weighted)', render: r => duration(r.avg_response_clocked_ms) },
    { key: 'revenue_per_hour', label: '$ / hour', align: 'right', hideBelow: 'lg', sortable: false, title: 'Not available: Infloww API exposes no worked hours', render: () => <span className="text-ink-3" title="Not exposed by the Infloww API">n/a</span> },
  ]

  // matrix
  const cells: any[] = m.data?.cells || []
  const emps = [...new Map(cells.map(c => [c.employee_id, c.employee || String(c.employee_id)])).entries()]
  const crs = [...new Map(cells.map(c => [c.platform_pid, c.creator || String(c.platform_pid)])).entries()]
  const maxCell = Math.max(1, ...cells.map(c => c.sales || 0))
  const cell = (e: number, p: number) => cells.find(c => c.employee_id === e && c.platform_pid === p)

  return (
    <div>
      <PageHeader title="Chatters" subtitle="Sales attribution, productivity and responsiveness by employee." meta={q.data.meta} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Attributed sales" value={money(totalSales)} sub={<span>{rows.filter(r => r.sales).length} chatters with sales</span>} />
        <Kpi label="Attribution coverage" value={pct(att.attributed_share)} unavailable={att.attributed_share == null ? 'No sales records synced' : undefined}
          sub={<span>{money(att.unassigned_amount, { compact: true })} unassigned</span>} tip="Share of recognised sales-record value Infloww attributed to an employee (transaction-perf salesRule ≠ Unassigned). Unassigned revenue is never given to anyone." />
        <Kpi label="Messages sent" value={num(msgs)} sub={<span>{num(ppvs)} PPVs · golden ratio {pct(msgs ? ppvs / msgs * 100 : null)}</span>} />
        <Kpi label="PPV unlock rate" value={pct(ppvs ? unlocked / ppvs * 100 : null)} sub={<span>{num(unlocked)} unlocked</span>} />
      </div>

      <Card className="mt-4" title="Chatter leaderboard" subtitle="Infloww-attributed sales per your Infloww sales settings">
        <DataTable rows={rows} columns={cols} rowKey={r => String(r.employee_id)} initialSort={{ key: 'sales', dir: 'desc' }} searchable searchPlaceholder="Search chatters…"
          onRowClick={r => nav(`/chatters/${r.employee_id}${search}`)} empty={<Empty title="No employees synced" />} />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Team sales trend" subtitle="Daily attributed sales (all chatters)">
          <TimeSeries data={q.data.trend} x="day" series={[{ key: 'sales', label: 'Sales', color: SERIES[0] }, { key: 'ppv', label: 'PPV', color: SERIES[1] }, { key: 'tips', label: 'Tips', color: SERIES[2] }]} area={false} height={260} />
        </Card>
        <Card title="How sales were attributed" subtitle="Infloww salesRule on sales records">
          {att.rules.length ? <BarList items={att.rules.map((r: any) => ({ key: r.rule, label: r.rule, value: r.amount, color: RULE_COLOR[r.rule] || SERIES[7], sub: `${num(r.n)} tx` }))} />
            : <Empty title="No sales records synced" />}
        </Card>
      </div>

      <Card className="mt-4" title="Creator × chatter matrix" subtitle="Attributed sales per chatter on each creator">
        {cells.length ? (
          <div className="-mx-5 overflow-x-auto px-5">
            <table className="text-[12px]">
              <thead><tr><th className="sticky left-0 bg-card py-1.5 pr-3 text-left text-[11px] font-medium text-ink-3 uppercase">Chatter</th>
                {crs.map(([p, n]) => <th key={p} className="px-1 py-1.5 text-center font-medium whitespace-nowrap text-ink-2">{n}</th>)}</tr></thead>
              <tbody>{emps.map(([e, n]) => (
                <tr key={e}><td className="sticky left-0 bg-card py-1 pr-3 whitespace-nowrap text-ink-2">{n}</td>
                  {crs.map(([p]) => { const c = cell(e, p); const v = c?.sales || 0; return (
                    <td key={p} className="p-0.5"><div title={`${n} → ${c?.creator || p}: ${money(v)}`} className="grid h-9 min-w-20 place-items-center rounded-md tabular"
                      style={{ background: v ? `color-mix(in oklab, var(--color-s1) ${Math.round(10 + 75 * v / maxCell)}%, var(--color-card))` : "var(--t-track)", color: v / maxCell > 0.8 ? "#fff" : "var(--color-ink)" }}>{v ? money(v, { compact: true }) : '·'}</div></td>) })}
                </tr>))}</tbody>
            </table>
          </div>
        ) : <Empty title="No chatter sales in range" />}
      </Card>
      <div className="mt-4"><Notes items={q.data.limitations} title="Data rules & limitations" /></div>
    </div>
  )
}
