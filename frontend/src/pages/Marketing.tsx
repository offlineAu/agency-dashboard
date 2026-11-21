import { useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { AlertTriangle, Pencil, Users, X } from 'lucide-react'
import { useState } from 'react'
import { BarList, SERIES } from '../components/charts'
import { DataTable, type Column } from '../components/DataTable'
import { Badge, Card, Empty, ErrorState, Kpi, Notes, PageHeader, PageSkeleton, Segmented } from '../components/ui'
import { apiGet, apiSend } from '../lib/api'
import { money, msDate, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

function CostEditor({ link, onClose }: { link: any; onClose: () => void }) {
  const qc = useQueryClient()
  const [cost, setCost] = useState(link.cost != null ? String(link.cost / 100) : '')
  const [date, setDate] = useState(link.spent_on || '')
  const [note, setNote] = useState(link.cost_note || '')
  const [err, setErr] = useState('')
  const save = async () => {
    const c = Number(cost)
    if (!Number.isFinite(c) || c < 0) { setErr('Enter a non-negative amount'); return }
    try {
      await apiSend('PUT', `/settings/campaign-costs/${link.link_type}/${link.id}`, { cost_cents: Math.round(c * 100), spent_on: date || null, note: note || null })
      qc.invalidateQueries(); onClose()
    } catch (e: any) { setErr(e.message) }
  }
  const clear = async () => { await apiSend('DELETE', `/settings/campaign-costs/${link.link_type}/${link.id}`); qc.invalidateQueries(); onClose() }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Edit promotional cost" className="w-full max-w-md rounded-2xl border border-line-2 bg-card p-5" onClick={e => e.stopPropagation()}>
        <div className="mb-1 flex items-center justify-between"><h3 className="font-semibold">Promotional cost</h3><button className="btn-icon" onClick={onClose} aria-label="Close"><X size={14} /></button></div>
        <p className="mb-4 text-xs text-ink-3">{link.name} · {link.creator_name}. Stored locally in this dashboard only — Infloww does not provide spend data and nothing is sent to Infloww.</p>
        <label className="mb-3 block text-xs text-ink-2">Total spend on this link (major units)<input autoFocus inputMode="decimal" className="input mt-1 w-full" value={cost} onChange={e => setCost(e.target.value)} placeholder="e.g. 250.00" /></label>
        <label className="mb-3 block text-xs text-ink-2">Spend date (used to place it in Financials)<input type="date" className="input mt-1 w-full" value={date} onChange={e => setDate(e.target.value)} /></label>
        <label className="mb-3 block text-xs text-ink-2">Note<input className="input mt-1 w-full" maxLength={200} value={note} onChange={e => setNote(e.target.value)} placeholder="Optional" /></label>
        {err && <div className="mb-2 text-xs text-bad">{err}</div>}
        <div className="flex justify-between gap-2">{link.cost != null ? <button className="btn" onClick={clear}>Remove cost</button> : <span />}<button className="btn-primary" onClick={save}>Save</button></div>
      </div>
    </div>
  )
}

function LinkFans({ link, onClose }: { link: any; onClose: () => void }) {
  const q = useQuery({ queryKey: ['linkfans', link.link_type, link.id], queryFn: () => apiGet(`/campaigns/${link.link_type}/${link.id}/fans`, { creator_id: link.creator_id }) })
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Link fans" className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-line-2 bg-card p-5" onClick={e => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between"><h3 className="font-semibold">Fans from “{link.name}”</h3><button className="btn-icon" onClick={onClose} aria-label="Close"><X size={14} /></button></div>
        {q.isLoading ? <div className="skeleton h-40" /> : !q.data?.available ? <Empty title="Unavailable">{q.data?.error?.message}</Empty> : (
          <>
            <p className="mb-3 text-xs text-ink-3">{num(q.data.total)} fans · fetched live · pseudonymised · earnings since subscribing via this link</p>
            <table className="w-full text-[13px]"><thead><tr className="text-[11px] text-ink-3 uppercase"><th className="pb-2 text-left font-medium">Fan</th><th className="pb-2 text-right font-medium">Earnings (gross)</th><th className="pb-2 text-right font-medium">Subscription</th><th className="pb-2 text-right font-medium">Messages</th><th className="pb-2 text-right font-medium">Subscribed</th></tr></thead>
              <tbody>{q.data.items.map((f: any) => <tr key={f.fan_ref} className="border-t border-line/60"><td className="py-1.5">{f.fan_name} <span className="text-[11px] text-ink-3">{f.fan_ref}</span></td><td className="text-right font-medium tabular">{money(f.earnings_gross)}</td><td className="text-right tabular">{money(f.subscription_gross)}</td><td className="text-right tabular">{money(f.messages_gross)}</td><td className="text-right tabular">{msDate(f.subscribed_ms)}</td></tr>)}</tbody></table>
          </>
        )}
      </div>
    </div>
  )
}

export default function Marketing() {
  const [type, setType] = useState<'' | 'TRACKING' | 'TRIAL' | 'CAMPAIGN'>('')
  const q = useDash('/campaigns', { link_type: type || undefined })
  const [edit, setEdit] = useState<any>(null)
  const [fans, setFans] = useState<any>(null)
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const s = d.summary
  const roiCell = (r: any) => r.roi == null ? <span className="text-ink-3">—</span> : <span className={r.roi >= 0 ? 'text-good' : 'text-bad'}>{pct(r.roi, 0)}</span>

  const cols: Column<any>[] = [
    { key: 'name', label: 'Link', render: r => <div className="max-w-64"><div className="truncate font-medium">{r.name}</div><div className="text-[11px] text-ink-3">{r.type_label} · {r.creator_name} {r.finished ? '· finished' : ''}</div></div> },
    { key: 'source', label: 'Source', hideBelow: 'md', render: r => r.source || <span className="text-ink-3">—</span> },
    { key: 'clicks', label: 'Clicks', align: 'right', render: r => num(r.clicks) },
    { key: 'subscribers', label: 'Subs / claims', align: 'right', title: 'Tracking: subscribers. Free trial: trial claims (not paid subscriptions).', render: r => num(r.subscribers) },
    { key: 'subscription_cvr', label: 'Sub CVR', align: 'right', hideBelow: 'md', render: r => pct(r.subscription_cvr, 2) },
    { key: 'paying_fans', label: 'Paying fans', align: 'right', hideBelow: 'lg', render: r => num(r.paying_fans) },
    { key: 'earnings', label: 'Earnings', align: 'right', render: r => <b>{money(r.earnings)}</b> },
    { key: 'epc', label: 'EPC', align: 'right', hideBelow: 'lg', render: r => money(r.epc) },
    { key: 'aeps', label: 'AEPS', align: 'right', hideBelow: 'lg', render: r => money(r.aeps) },
    { key: 'cost', label: 'Cost', align: 'right', render: r => <button className="inline-flex items-center gap-1 hover:text-ink" onClick={e => { e.stopPropagation(); setEdit(r) }} aria-label={`Edit cost for ${r.name}`}>{r.cost == null ? <span className="text-ink-3">add</span> : money(r.cost)}<Pencil size={11} className="text-ink-3" /></button> },
    { key: 'cpc', label: 'CPC', align: 'right', hideBelow: 'lg', render: r => money(r.cpc) },
    { key: 'cps', label: 'CPS', align: 'right', hideBelow: 'lg', render: r => money(r.cps) },
    { key: 'profit', label: 'Profit', align: 'right', hideBelow: 'md', render: r => r.profit == null ? <span className="text-ink-3">—</span> : <span className={r.profit >= 0 ? 'text-good' : 'text-bad'}>{money(r.profit)}</span> },
    { key: 'roi', label: 'ROI', align: 'right', render: roiCell },
    { key: 'fans', label: '', sortable: false, render: r => <button className="btn-icon" title="View fans from this link" aria-label="View fans" onClick={e => { e.stopPropagation(); setFans(r) }}><Users size={13} /></button> },
  ]

  return (
    <div>
      <PageHeader title="Marketing & promotion" subtitle="Tracking links, free trials and profile promotions — what acquisition actually earns. Infloww reports link metrics as lifetime totals, so figures here ignore the date range." meta={d.meta}
        actions={<Segmented size="sm" value={type} onChange={setType} options={[{ value: '', label: 'All' }, { value: 'TRACKING', label: 'Tracking' }, { value: 'TRIAL', label: 'Free trial' }, { value: 'CAMPAIGN', label: 'Promotions' }]} />} />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Clicks (tracking links)" value={num(s.clicks)} sub={<span>{num(s.links)} links</span>} />
        <Kpi label="Subscribers acquired" value={num(s.subscribers)} sub={<span>{num(s.trial_claims)} are free-trial claims · CVR {pct(s.subscription_cvr, 2)}</span>} />
        <Kpi label="Attributed earnings" value={money(s.earnings)} sub={<span>EPC {money(s.epc)} · AEPS {money(s.aeps)}</span>} tip="Cumulative earnings Infloww attributes to each link (fan's most recent link — rolling attribution)." />
        <Kpi label="Campaign ROI" value={s.roi == null ? '—' : pct(s.roi, 0)} unavailable={s.cost == null ? 'Add link costs to compute ROI' : undefined}
          sub={<span>spend {money(s.cost)} on {s.costed_links} links · profit {money(s.profit)}</span>} tip="Profit ÷ cost × 100, only over links with a locally-entered cost. Infloww does not provide spend." />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Earnings by traffic source"><BarList items={d.by_source.slice(0, 8).map((x: any, i: number) => ({ key: x.source, label: x.source, value: x.earnings, color: SERIES[i % 8], sub: `${num(x.subscribers)} subs` }))} /></Card>
        <Card title="Acquisition by creator"><BarList fmt="num" items={d.by_creator.slice(0, 8).map((x: any) => ({ key: x.creator, label: x.creator, value: x.subscribers, sub: money(x.earnings, { compact: true }) }))} /></Card>
        <Card title="Needs attention" subtitle="Negative ROI, CVR under half the median, or clicks with no subs">
          {d.underperforming.length ? (
            <ul className="space-y-2.5">{d.underperforming.slice(0, 8).map((u: any) => (
              <li key={u.link_type + u.id} className="flex gap-2 text-[13px]"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-warn" />
                <div><div className="font-medium">{u.name} <span className="text-[11px] font-normal text-ink-3">{u.creator_name}</span></div><div className="text-xs text-ink-3">{u.reasons.join(' · ')}</div></div></li>))}
            </ul>) : <Empty title="No underperforming links flagged" />}
        </Card>
      </div>
      <Card className="mt-4" title="Campaign leaderboard" subtitle={<span>Cumulative figures per link. <Badge tone="accent">Local input</Badge> costs drive CPC, CPS, profit and ROI.</span>}>
        <DataTable rows={d.items} columns={cols} rowKey={r => r.link_type + r.id} initialSort={{ key: 'earnings', dir: 'desc' }} searchable searchPlaceholder="Search links, sources, creators…"
          empty={<Empty title={d.meta.syncing ? 'Syncing links…' : 'No links synced'} />} />
      </Card>
      <div className={clsx('mt-4')}><Notes items={[...d.notes, 'Formulas: CVR = subs ÷ clicks; CPC = cost ÷ clicks; CPS = cost ÷ subs; EPC = earnings ÷ clicks; AEPS = earnings ÷ subs; Profit = earnings − cost; ROI = profit ÷ cost.']} /></div>
      {edit && <CostEditor link={edit} onClose={() => setEdit(null)} />}
      {fans && <LinkFans link={fans} onClose={() => setFans(null)} />}
    </div>
  )
}
