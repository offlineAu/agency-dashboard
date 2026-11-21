import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { BarList, SERIES, ShareBar, TimeSeries, TYPE_COLOR } from '../components/charts'
import { DataTable } from '../components/DataTable'
import { Avatar, AvatarEditor } from '../components/Avatar'
import { Badge, Card, Delta, Empty, ErrorState, Kpi, PageHeader, PageSkeleton } from '../components/ui'
import { apiGet } from '../lib/api'
import { useFilters, useFilterSearch } from '../lib/filters'
import { duration, money, num, pct, shortDate } from '../lib/format'
import { useDash } from '../lib/hooks'

export default function CreatorDetail() {
  const { id } = useParams()
  const f = useFilters()
  const search = useFilterSearch()
  const q = useDash(`/creators/${id}`)
  const chat = useQuery({ queryKey: ['chat', id, f.start, f.end], queryFn: () => apiGet(`/creators/${id}/chat`, { start: f.start, end: f.end }), staleTime: 5 * 60_000 })
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const c = d.creator
  const cur = d.totals.current
  const g = d.totals.growth
  const a = d.audience
  const ch = chat.data?.rows?.[0]
  const basis = f.basis === 'net' ? 'Net' : 'Gross'

  return (
    <div>
      <Link to={`/creators${search}`} className="mb-3 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink-2"><ArrowLeft size={13} />All creators</Link>
      <PageHeader title={c.name || `Creator ${c.id}`} meta={d.meta} avatar={<AvatarEditor kind="creator" id={c.id} name={c.name} size={60} />}
        subtitle={<span className="flex flex-wrap items-center gap-2">@{c.user_name} · ID {c.id} · PID {c.platform_pid}<Badge tone={c.connected ? 'good' : 'warn'}>{c.status || (c.connected ? 'connected' : 'not connected')}</Badge></span>} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label={`${basis} revenue`} value={money(cur.value)} delta={<Delta g={g.value} label="vs prev." />} sub={<span>{pct(d.share_of_agency)} of agency</span>} />
        <Kpi label="Paying fans" value={num(cur.paying_fans)} delta={<Delta g={g.paying_fans} />} sub={<span>{money(cur.paying_fans ? cur.value / cur.paying_fans : null)} avg spend</span>} />
        <Kpi label="Active fans" value={num(a.activeFans)} unavailable={a.activeFans == null ? 'No creator report data' : undefined} sub={<span>{num(a.expiredFans)} expired · as of {a.activeFans_asof ? shortDate(a.activeFans_asof) : '—'}</span>} />
        <Kpi label="Auto-renew on" value={pct(a.autoRenewPct)} unavailable={a.autoRenewPct == null ? 'No creator report data' : undefined}
          sub={<span>{num(a.fansWithRenewOn)} fans · avg sub {num(a.avgSubscriptionLength)} days</span>} tip="Fans with auto-renew enabled ÷ active fans on the latest reported day." />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="New subscribers" value={num(a.newSubscribers)} sub={<span>{num(a.subscriberRenewals)} renewals</span>} />
        <Kpi label="PPV revenue" value={money(cur.ppv)} delta={<Delta g={g.ppv} />} />
        <Kpi label="Tips" value={money(cur.tips)} delta={<Delta g={g.tips} />} />
        <Kpi label="Refunds & reversals" value={money(cur.refunds + cur.reversed)} sub={<span>pending return {money(cur.pending_return)}</span>} />
      </div>

      <Card className="mt-4" title="Revenue history" subtitle={`${basis} revenue per day`}>
        <TimeSeries data={d.trend} series={[{ key: 'value', label: `${basis} revenue`, color: SERIES[0] }]} />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Revenue breakdown">{d.breakdown.length ? <ShareBar items={d.breakdown.map((b: any) => ({ key: b.type, label: b.label, value: b.value, color: TYPE_COLOR[b.type] || '#5b6380' }))} /> : <Empty title="No revenue in range" />}</Card>
        <Card title="Engagement" subtitle="Creator-account chat activity (Infloww creator report, fetched live for this range)">
          {chat.isLoading ? <div className="flex items-center gap-2 text-sm text-ink-3"><Loader2 size={14} className="animate-spin" />Loading…</div>
            : !chat.data?.available ? <Empty title="Chat summary unavailable">{chat.data?.error?.message}</Empty>
            : !ch ? <Empty title="No chat activity reported" />
            : (
              <div className="grid grid-cols-2 gap-4">
                {[['Messages sent', num(ch.messages_sent)], ['PPVs sent', num(ch.ppvs_sent)], ['Avg reply time', duration(ch.reply_ms)],
                  ['Fans chatted', num(ch.fans_chatted_sum)], ['PPV share of messages', pct(ch.messages_sent ? ch.ppvs_sent / ch.messages_sent * 100 : null)],
                  ['PPV revenue / PPV sent', money(ch.ppvs_sent ? cur.ppv_messages / ch.ppvs_sent : null)]].map(([l, v]) => (
                  <div key={l as string}><div className="text-[11px] text-ink-3 uppercase">{l}</div><div className="mt-0.5 text-lg font-semibold tabular">{v}</div></div>
                ))}
              </div>
            )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Subscriber growth & retention" subtitle="Daily, from Infloww creator reports">
          {d.audience_daily.length ? (<>
            <TimeSeries data={d.audience_daily} x="day" fmt="num" area={false} height={240} series={[
              { key: 'activeFans', label: 'Active fans', color: SERIES[0] }, { key: 'expiredFans', label: 'Expired fans', color: SERIES[1] }, { key: 'fansWithRenewOn', label: 'Auto-renew on', color: SERIES[2] }]} />
          </>) : <Empty title="No creator report data in range" />}
        </Card>
        <Card title="New subscribers vs renewals">
          {d.audience_daily.length ? (
            <TimeSeries data={d.audience_daily} x="day" fmt="num" area={false} height={240} series={[
              { key: 'newSubscribers', label: 'New subscribers', color: SERIES[2] }, { key: 'subscriberRenewals', label: 'Renewals', color: SERIES[6] }]} />
          ) : <Empty title="No creator report data in range" />}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Top spenders" subtitle="Pseudonymised · spend in range">
          <DataTable rows={d.top_spenders} rowKey={r => r.fan_id} pageSize={10} empty={<Empty title="No paying fans in range" />} columns={[
            { key: 'fan_name', label: 'Fan', render: r => <span>{r.fan_name || '—'} <span className="text-[11px] text-ink-3">{r.fan_id}</span></span> },
            { key: 'value', label: 'Spend', align: 'right', render: r => <b>{money(r.value)}</b> },
            { key: 'n', label: 'Purchases', align: 'right', render: r => num(r.n) },
            { key: 'ppv_purchases', label: 'PPV buys', align: 'right', render: r => num(r.ppv_purchases) },
          ]} />
        </Card>
        <Card title="Chatters on this creator" subtitle="Infloww-attributed sales">
          {d.employees.length ? <BarList items={d.employees.map((e: any) => ({ key: String(e.employee_id), label: e.name || e.employee_id, value: e.sales, lead: <Avatar kind="employee" id={e.employee_id} name={e.name} size={30} /> }))} /> : <Empty title="No attributed sales" />}
        </Card>
      </div>

      <Card className="mt-4" title="Marketing" subtitle="Links for this creator · cumulative earnings">
        {d.top_links.length ? (
          <DataTable rows={d.top_links} rowKey={r => r.link_type + r.id} pageSize={5} columns={[
            { key: 'name', label: 'Link', render: r => <span>{r.name} <span className="text-[11px] text-ink-3">{r.type_label}</span></span> },
            { key: 'clicks', label: 'Clicks', align: 'right', render: r => num(r.clicks) },
            { key: 'subscribers', label: 'Subs', align: 'right', render: r => num(r.subscribers) },
            { key: 'earnings', label: 'Earnings', align: 'right', render: r => money(r.earnings) },
            { key: 'roi', label: 'ROI', align: 'right', render: r => r.roi == null ? <span className="text-ink-3">no cost</span> : pct(r.roi, 0) },
          ]} />
        ) : <Empty title="No links synced for this creator" />}
      </Card>
    </div>
  )
}
