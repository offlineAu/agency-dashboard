import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { BarList, SERIES, TimeSeries } from '../components/charts'
import { AvatarEditor } from '../components/Avatar'
import { Badge, Card, Delta, Empty, ErrorState, Kpi, PageHeader, PageSkeleton } from '../components/ui'
import { useFilterSearch } from '../lib/filters'
import { duration, money, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

export default function ChatterDetail() {
  const { id } = useParams()
  const search = useFilterSearch()
  const q = useDash(`/employees/${id}`)
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const s = d.summary || {}
  return (
    <div>
      <Link to={`/chatters${search}`} className="mb-3 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink-2"><ArrowLeft size={13} />All chatters</Link>
      <PageHeader title={d.employee.name} meta={d.meta} avatar={<AvatarEditor kind="employee" id={d.employee.employee_id} name={d.employee.name} size={60} />}
        subtitle={<span className="flex flex-wrap items-center gap-2">Employee ID {d.employee.employee_id}<Badge tone={d.employee.status === 'Activated' ? 'good' : 'neutral'}>{d.employee.status}</Badge>{s.rank && <Badge tone="accent">Rank #{s.rank}</Badge>}</span>} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Attributed sales" value={money(s.sales)} delta={<Delta g={s.growth} label="vs prev." />} />
        <Kpi label="PPV / Tips" value={money(s.ppv_sales)} sub={<span>tips {money(s.tips_sales)}</span>} />
        <Kpi label="Messages sent" value={num(s.messages_sent)} sub={<span>{num(s.ppvs_sent)} PPVs · {money(s.sales_per_message)} / msg</span>} />
        <Kpi label="Avg reply time" value={duration(s.avg_response_clocked_ms)} sub={<span>scheduled-hours basis {duration(s.avg_response_scheduled_ms)}</span>} tip="Message-weighted average of Infloww's daily reply-time figures." />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Unlock rate" value={pct(s.unlock_rate)} sub={<span>{num(s.ppvs_unlocked)} unlocked</span>} />
        <Kpi label="Golden ratio" value={pct(s.golden_ratio)} tip="PPVs sent ÷ direct messages sent" />
        <Kpi label="Fans chatted" value={num(s.fans_chatted_daily_sum)} tip="Sum of daily unique fans; a fan chatted on several days counts once per day." />
        <Kpi label="Revenue / hour" value="—" unavailable="Worked hours not exposed by Infloww API" />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Performance trend" subtitle="Daily attributed sales">
          <TimeSeries data={d.trend} x="day" series={[{ key: 'sales', label: 'Sales', color: SERIES[0] }, { key: 'ppv', label: 'PPV', color: SERIES[1] }]} area={false} height={260} />
        </Card>
        <Card title="Sales by creator">
          {d.by_creator.length ? <BarList items={d.by_creator.map((c: any) => ({ key: String(c.platform_pid), label: c.creator || c.platform_pid, value: c.sales }))} /> : <Empty title="No sales in range" />}
          <div className="mt-4 text-[11px] text-ink-3">Assigned: {s.assigned_creators?.map((c: any) => c.name || c.id).join(', ') || '—'}</div>
        </Card>
      </div>
      <Card className="mt-4" title="Chat activity" subtitle="Daily direct messages, PPVs sent and unlocked">
        <TimeSeries data={d.chat_daily} x="day" fmt="num" area={false} height={240} series={[
          { key: 'messages', label: 'Messages', color: SERIES[0] }, { key: 'ppvs_sent', label: 'PPVs sent', color: SERIES[1] }, { key: 'ppvs_unlocked', label: 'PPVs unlocked', color: SERIES[2] }]} />
      </Card>
    </div>
  )
}
