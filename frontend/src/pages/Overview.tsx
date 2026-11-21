import { ArrowRight, CircleDollarSign, Crown, FileText, Heart, MessagesSquare, Sparkles, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Avatar, AvatarEditor, AvatarStack } from '../components/Avatar'
import { Bars, BarList, Donut, Gauge, SERIES, Sparkline, TimeSeries, TYPE_COLOR } from '../components/charts'
import { Card, DataStatus, Delta, Empty, ErrorState, Kpi, PageSkeleton, Segmented } from '../components/ui'
import { useFilters, useFilterSearch } from '../lib/filters'
import { money, num, pct, shortDate } from '../lib/format'
import { useDash } from '../lib/hooks'

/** Hero illustration: a floating revenue card, coins and chat bubble. Pure SVG, decorative. */
function HeroArt() {
  return (
    <svg viewBox="0 0 260 190" className="pointer-events-none absolute right-2 bottom-0 hidden h-[88%] max-h-52 sm:block" aria-hidden="true">
      <defs>
        <linearGradient id="hc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".95" /><stop offset="1" stopColor="#fff" stopOpacity=".75" /></linearGradient>
        <linearGradient id="hb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8b5cf6" /><stop offset="1" stopColor="#6366f1" stopOpacity=".55" /></linearGradient>
        <linearGradient id="coin" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#fde68a" /><stop offset="1" stopColor="#f59e0b" /></linearGradient>
        <filter id="sh" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="8" stdDeviation="8" floodColor="#1e1b4b" floodOpacity=".25" /></filter>
      </defs>
      <circle cx="170" cy="96" r="84" fill="#fff" fillOpacity=".08" />
      <circle cx="170" cy="96" r="58" fill="#fff" fillOpacity=".07" />
      <g filter="url(#sh)" transform="rotate(-6 150 100)">
        <rect x="78" y="42" width="140" height="104" rx="16" fill="url(#hc)" />
        <rect x="94" y="58" width="52" height="7" rx="3.5" fill="#c7d2fe" />
        <rect x="94" y="70" width="32" height="6" rx="3" fill="#e0e7ff" />
        {[22, 34, 26, 44, 38, 54].map((h, i) => <rect key={i} x={98 + i * 19} y={132 - h} width="11" height={h} rx="5.5" fill="url(#hb)" />)}
      </g>
      <g filter="url(#sh)">
        <ellipse cx="64" cy="150" rx="26" ry="8" fill="#d97706" /><rect x="38" y="134" width="52" height="16" fill="#f59e0b" /><ellipse cx="64" cy="134" rx="26" ry="8" fill="url(#coin)" />
        <ellipse cx="64" cy="126" rx="26" ry="8" fill="#d97706" /><rect x="38" y="110" width="52" height="16" fill="#f59e0b" /><ellipse cx="64" cy="110" rx="26" ry="8" fill="url(#coin)" />
        <text x="64" y="114" textAnchor="middle" fontSize="11" fontWeight="700" fill="#92400e">$</text>
      </g>
      <g filter="url(#sh)">
        <path d="M206 18h38a10 10 0 0 1 10 10v18a10 10 0 0 1-10 10h-22l-10 9v-9h-6a10 10 0 0 1-10-10V28a10 10 0 0 1 10-10z" fill="#fff" />
        <path d="M225 45c-6-4.5-10-8-10-11.6 0-2.5 2-4.4 4.4-4.4 1.6 0 3.1.9 3.8 2.2h.1c.7-1.3 2.2-2.2 3.8-2.2 2.4 0 4.4 1.9 4.4 4.4 0 3.6-4 7.1-10 11.6z" fill="#ec4899" />
      </g>
      <path d="M40 40l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="#fff" fillOpacity=".85" />
      <path d="M246 120l2 4.5 4.5 2-4.5 2-2 4.5-2-4.5-4.5-2 4.5-2z" fill="#fff" fillOpacity=".7" />
    </svg>
  )
}

export default function Overview() {
  const f = useFilters()
  const search = useFilterSearch()
  const nav = useNavigate()
  const [gran, setGran] = useState<'day' | 'week' | 'month'>('day')
  const q = useDash('/dashboard/overview')
  const rev = useDash('/dashboard/revenue', { granularity: gran }, { enabled: gran !== 'day' })
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const k = d.kpis
  const cur = k.revenue.current
  const g = k.revenue.growth
  const prevLabel = 'vs prev. period'
  const basisLabel = f.basis === 'net' ? 'Net' : 'Gross'
  const trend = gran === 'day' ? d.trend : rev.data?.trend || []
  const noData = !cur.transactions && !k.active_creators
  const top = d.top_creators.filter((c: any) => c.revenue)
  const star = top[0]
  const attributedPct = cur.gross && k.employee_attributed_sales != null ? (k.employee_attributed_sales / cur.gross) * 100 : null

  return (
    <div className={q.isFetching && !q.isLoading ? 'opacity-90 transition-opacity' : ''}>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-[26px]">Agency overview</h1>
          <p className="mt-1 text-sm text-ink-2">Revenue, audience and team performance across all managed creators.</p>
        </div>
        <DataStatus meta={d.meta} />
      </div>
      {noData && d.meta.configured && !d.meta.syncing && (
        <Card className="mb-4"><Empty title="No synced data for this range yet">Data appears after the first sync completes. Check API Status if this persists.</Empty></Card>
      )}

      {/* Hero + spotlight */}
      <div className="grid gap-4 lg:grid-cols-3">
        <section data-testid="hero-revenue" className="rise relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#4f46e5] via-[#6d5dfc] to-[#a78bfa] p-6 text-white shadow-xl shadow-accent/25 sm:p-7 lg:col-span-2">
          <div aria-hidden="true" className="pointer-events-none absolute -top-24 -left-16 size-64 rounded-full bg-white/10 blur-2xl" />
          <HeroArt />
          <div className="relative max-w-md">
            <div className="text-sm font-medium text-white/80">{basisLabel} revenue · {shortDate(f.start)} – {shortDate(f.end)}</div>
            <div className="mt-2 text-4xl font-bold tracking-tight tabular sm:text-[44px]">{money(cur.value)}</div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-white/85 [&_.delta]:bg-white/20 [&_.delta]:text-white [&_.delta-label]:text-white/80 [&_.delta-none]:text-white/80">
              <Delta g={g.value} label={prevLabel} /><span className="text-white/60">·</span><span>{num(cur.transactions)} transactions from {num(cur.paying_fans)} paying fans</span>
            </div>
            {top.length > 0 && (
              <div className="mt-5 flex items-center gap-3">
                <AvatarStack people={top.slice(0, 5).map((c: any) => ({ kind: 'creator' as const, id: c.id, name: c.name }))} size={36} />
                <span className="text-xs text-white/80">{top.length} creator{top.length > 1 ? 's' : ''} earning this period</span>
              </div>
            )}
            <div className="mt-6 flex flex-wrap gap-2">
              <Link to={`/creators${search}`} className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-[13px] font-semibold text-[#4338ca] shadow-sm hover:bg-white/90">View creators<ArrowRight size={15} /></Link>
              <Link to={`/reports${search}`} className="inline-flex items-center gap-1.5 rounded-xl bg-white/15 px-4 py-2 text-[13px] font-semibold text-white ring-1 ring-white/30 hover:bg-white/25"><FileText size={15} />Reports</Link>
            </div>
          </div>
        </section>

        <section className="card rise relative overflow-hidden">
          <div aria-hidden="true" className="h-24 bg-gradient-to-r from-[#c7d2fe] via-[#e9d5ff] to-[#fbcfe8] dark:opacity-40" />
          {star ? (
            <div className="-mt-12 flex flex-col items-center px-5 pb-5 text-center">
              <div className="rounded-full bg-card p-1.5 shadow-md"><AvatarEditor kind="creator" id={star.id} name={star.name} size={84} /></div>
              <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-s4/15 px-2 py-0.5 text-[11px] font-semibold text-warn"><Crown size={12} />Top creator</div>
              <div className="mt-1.5 text-lg font-semibold">{star.name}</div>
              {star.user_name && <div className="text-xs text-ink-3">@{star.user_name}</div>}
              <div className="mt-4 grid w-full grid-cols-2 gap-2">
                <div className="rounded-2xl bg-card-2 p-3"><div className="text-[11px] text-ink-3">{basisLabel} revenue</div><div className="mt-0.5 font-semibold tabular">{money(star.revenue, { compact: true })}</div></div>
                <div className="rounded-2xl bg-card-2 p-3"><div className="text-[11px] text-ink-3">Share of agency</div><div className="mt-0.5 font-semibold tabular">{pct(star.share_of_agency, 0)}</div></div>
              </div>
              <div className="mt-2"><Delta g={star.growth} label={prevLabel} /></div>
              <Link to={`/creators/${star.id}${search}`} className="btn-primary mt-4 w-full justify-center">View profile<ArrowRight size={15} /></Link>
            </div>
          ) : <Empty title="No creator revenue in range" icon={<Sparkles size={20} />} />}
        </section>
      </div>

      {/* KPI rows */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi featured label={f.basis === 'net' ? 'Gross revenue' : 'Net revenue'} icon={<CircleDollarSign size={18} />} value={money(f.basis === 'net' ? cur.gross : cur.net)}
          spark={<Sparkline data={d.trend} k={f.basis === 'net' ? 'gross' : 'net'} light />}
          sub={<span>{money(cur.platform_fees, { compact: true })} platform fees · {num(cur.paying_fans)} paying fans</span>}
          tip="Net = gross fan spend minus the OnlyFans platform fee, as reported per transaction by Infloww. Same recognition rules as gross." />
        <Kpi label="Active fans" icon={<Heart size={18} />} tone="s5" value={num(k.active_fans)}
          unavailable={k.active_fans == null ? 'Creator reports not synced' : undefined}
          spark={<Sparkline data={d.subscriber_trend} k="activeFans" color={SERIES[4]} />}
          sub={<span>{num(k.audience_creators_reporting)}/{num(k.audience_creators_total)} creators reporting · latest day</span>}
          tip="Sum of each creator's active-fan count on the latest reported day in the range (Infloww creator report, up to 24h delayed)." />
        <Kpi label="New subscribers" icon={<UserPlus size={18} />} tone="s3" value={num(k.new_subscribers)}
          unavailable={k.new_subscribers == null ? 'Creator reports not synced' : undefined}
          spark={<Sparkline data={d.subscriber_trend} k="newSubscribers" color={SERIES[2]} />}
          sub={<span>{num(k.renewals)} renewals · auto-renew {pct(k.auto_renew_pct)}</span>} tip="New subscribers and renewals summed over the range from Infloww creator reports." />
        <Kpi label="Chatter-attributed sales" icon={<MessagesSquare size={18} />} tone="s1" value={money(k.employee_attributed_sales)}
          unavailable={k.employee_attributed_sales == null ? 'No employee report data' : undefined}
          sub={<span>{attributedPct == null ? '—' : pct(attributedPct)} of gross</span>}
          tip="Sales Infloww attributes to employees per your Infloww sales settings. Creator revenue is never redistributed to chatters." />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Kpi label="Subscriptions" value={money(cur.subscription)} delta={<Delta g={g.subscription} />} sub={<span>new {money(cur.subscription_new, { compact: true })} · recurring {money(cur.subscription_recurring, { compact: true })}</span>} />
        <Kpi label="PPV (messages + posts)" value={money(cur.ppv)} delta={<Delta g={g.ppv} />} sub={<span>msgs {money(cur.ppv_messages, { compact: true })} · posts {money(cur.ppv_posts, { compact: true })}</span>} />
        <Kpi label="Tips" value={money(cur.tips)} delta={<Delta g={g.tips} />} />
        <Kpi label="Refunds & reversals" value={money(cur.refunds + cur.reversed)} delta={<Delta g={g.refunds} invert />}
          sub={<span>refunds {money(cur.refunds, { compact: true })} · reversed {money(cur.reversed, { compact: true })}</span>}
          tip="Refunds from /v1/refunds (by refund date) plus transactions with status 'undo'. The API does not separate chargebacks from refunds." />
      </div>

      {/* Revenue + sources */}
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Revenue performance" subtitle={`${basisLabel} revenue per ${gran} · ${money(cur.value)} total · ${num(cur.transactions)} transactions`}
          action={<Segmented size="sm" value={gran} onChange={setGran} options={[{ value: 'day', label: 'Daily' }, { value: 'week', label: 'Weekly' }, { value: 'month', label: 'Monthly' }]} />}>
          <TimeSeries data={trend} series={[{ key: 'value', label: `${basisLabel} revenue`, color: SERIES[0] }]} height={300} />
        </Card>
        <Card title="Revenue by source" subtitle={`Share of ${basisLabel.toLowerCase()} revenue`} action={<Link to={`/revenue${search}`} className="link text-xs">Financials →</Link>}>
          {d.breakdown.length ? <Donut centerLabel={`${basisLabel} total`} items={d.breakdown.map((b: any) => ({ key: b.type, label: b.label, value: b.value, color: TYPE_COLOR[b.type] || TYPE_COLOR.Unknown }))} /> : <Empty title="No revenue in range" />}
        </Card>
      </div>

      {/* People */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <Card title="Top creators" subtitle={`By ${basisLabel.toLowerCase()} revenue · share of agency`} action={<Link to={`/creators${search}`} className="link text-xs">All creators →</Link>}>
          {top.length ? (
            <BarList onClick={id => nav(`/creators/${id}${search}`)} items={top.slice(0, 6).map((c: any) => ({
              key: c.id, label: c.name || c.id, value: c.revenue, sub: pct(c.share_of_agency, 0), lead: <Avatar kind="creator" id={c.id} name={c.name} size={34} />,
            }))} />
          ) : <Empty title="No creator revenue in range" />}
        </Card>
        <Card title="Chatter leaderboard" subtitle="Infloww-attributed sales" action={<Link to={`/chatters${search}`} className="link text-xs">All →</Link>}>
          {d.top_employees.some((e: any) => e.sales) ? (
            <ol className="space-y-1">
              {d.top_employees.slice(0, 6).map((e: any, i: number) => (
                <li key={e.employee_id}>
                  <Link to={`/chatters/${e.employee_id}${search}`} className="flex items-center gap-3 rounded-xl p-1.5 hover:bg-ink/5">
                    <span className="relative">
                      <Avatar kind="employee" id={e.employee_id} name={e.name} size={36} />
                      <span className={`absolute -right-1 -bottom-1 grid size-[18px] place-items-center rounded-full text-[10px] font-bold ring-2 ring-card ${i === 0 ? 'bg-[#f59e0b] text-white' : i === 1 ? 'bg-[#94a3b8] text-white' : i === 2 ? 'bg-[#c2410c] text-white' : 'bg-card-2 text-ink-3'}`}>{i + 1}</span>
                    </span>
                    <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-medium">{e.name}</span><span className="text-[11px] text-ink-3">{num(e.messages_sent)} msgs · unlock {pct(e.unlock_rate, 0)}</span></span>
                    <span className="text-right"><span className="block text-[13px] font-semibold tabular">{money(e.sales, { compact: true })}</span><Delta g={e.growth} /></span>
                  </Link>
                </li>
              ))}
            </ol>
          ) : <Empty title="No attributed sales in range" />}
        </Card>
        <Card title="Attribution coverage" subtitle="Share of gross revenue Infloww credits to a chatter" className="lg:col-span-2 xl:col-span-1">
          <div className="pt-2">
            <Gauge value={attributedPct} label="Attributed to chatters" sub={<>{money(k.employee_attributed_sales, { compact: true })} of {money(cur.gross, { compact: true })} gross</>} />
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 text-center">
            <div className="rounded-2xl bg-card-2 p-3"><div className="text-[11px] text-ink-3">Attributed</div><div className="mt-0.5 font-semibold tabular">{money(k.employee_attributed_sales, { compact: true })}</div></div>
            <div className="rounded-2xl bg-card-2 p-3"><div className="text-[11px] text-ink-3">Unattributed</div><div className="mt-0.5 font-semibold tabular">{attributedPct == null ? '—' : money(Math.max(0, cur.gross - (k.employee_attributed_sales || 0)), { compact: true })}</div></div>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Subscriber growth" subtitle={`New subscribers per day · ${num(k.new_subscribers)} total · ${num(k.renewals)} renewals (Infloww creator reports)`}>
          {d.subscriber_trend.length ? (
            <Bars data={d.subscriber_trend} x="day" y="newSubscribers" fmt="num" height={240} color={SERIES[2]} labelFmt={v => shortDate(String(v))} />
          ) : <Empty title="No creator report data in range" icon={<Users size={20} />}>Creator reports are delayed up to 24h by Infloww.</Empty>}
        </Card>
        <Card title="Top campaigns" subtitle="Lifetime link earnings (cumulative)" action={<Link to={`/marketing${search}`} className="link text-xs">Marketing →</Link>}>
          {d.top_campaigns.length ? (
            <ul className="space-y-2">
              {d.top_campaigns.slice(0, 5).map((c: any) => (
                <li key={c.link_type + c.id} className="flex items-center gap-3 rounded-2xl bg-card-2 p-2.5">
                  <Avatar kind="creator" id={c.creator_id} name={c.creator_name} size={34} />
                  <div className="min-w-0 flex-1"><div className="truncate text-[13px] font-medium">{c.name}</div><div className="truncate text-[11px] text-ink-3">{c.creator_name} · {c.source || 'no source'} · {num(c.subscribers)} {c.link_type === 'TRIAL' ? 'claims' : 'subs'}</div></div>
                  <div className="text-right text-[13px] font-semibold tabular">{money(c.earnings, { compact: true })}</div>
                </li>
              ))}
            </ul>
          ) : <Empty title="No tracking or trial links synced" icon={<Sparkles size={20} />} />}
        </Card>
      </div>
    </div>
  )
}
