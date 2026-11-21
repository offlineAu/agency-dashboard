import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { AvatarEditor } from '../components/Avatar'
import { Card, ErrorState, PageSkeleton, PageHeader } from '../components/ui'
import { useMeta } from '../lib/hooks'
import { apiGet, apiSend, getToken, setToken } from '../lib/api'
import { money } from '../lib/format'

function Photos() {
  const meta = useMeta()
  const [tab, setTab] = useState<'creator' | 'employee'>('creator')
  const [q, setQ] = useState('')
  const creators = (meta.data?.creators || []).filter((c: any) => c.connected).map((c: any) => ({ id: c.id, name: c.name, sub: c.user_name ? `@${c.user_name}` : '' }))
  const emps = (meta.data?.employees || []).filter((e: any) => e.status === 'Activated').map((e: any) => ({ id: String(e.employee_id), name: e.name, sub: 'Chatter' }))
  const list = (tab === 'creator' ? creators : emps).filter((p: any) => (p.name || '').toLowerCase().includes(q.toLowerCase()))
  const withPhoto = Object.keys(meta.data?.avatars || {}).filter(k => k.startsWith(tab + ':')).length
  return (
    <Card className="mt-4" title="Photos" subtitle="Infloww's API has no profile pictures. Upload real photos here (PNG, JPEG or WebP, up to 2 MB). They're stored only on this server and never sent to Infloww."
      action={<div className="flex gap-2">
        <div role="tablist" className="inline-flex rounded-xl bg-card-2 p-1 ring-1 ring-line">
          {(['creator', 'employee'] as const).map(t => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1 text-xs font-medium ${tab === t ? 'bg-card text-ink shadow-sm ring-1 ring-line-2' : 'text-ink-3'}`}>{t === 'creator' ? 'Creators' : 'Chatters'}</button>)}
        </div>
        <input className="input w-40" placeholder="Filter…" value={q} onChange={e => setQ(e.target.value)} aria-label="Filter people" />
      </div>}>
      <div className="mb-3 text-xs text-ink-3">{withPhoto} of {tab === 'creator' ? creators.length : emps.length} {tab === 'creator' ? 'creators' : 'active chatters'} have a photo. Click an avatar to add or change it.</div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {list.slice(0, 60).map((p: any) => (
          <div key={p.id} className="flex items-center gap-3 rounded-2xl bg-card-2 p-3">
            <AvatarEditor kind={tab} id={p.id} name={p.name} size={44} />
            <div className="min-w-0"><div className="truncate text-[13px] font-medium">{p.name}</div><div className="truncate text-[11px] text-ink-3">{p.sub}</div></div>
          </div>
        ))}
      </div>
      {list.length > 60 && <div className="mt-2 text-xs text-ink-3">Showing 60 of {list.length}. Use the filter to find someone.</div>}
    </Card>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <label className="block text-[13px]"><span className="text-ink-2">{label}</span>{children}{hint && <span className="mt-1 block text-[11px] text-ink-3">{hint}</span>}</label>
}

export default function Settings() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['settings'], queryFn: () => apiGet('/settings') })
  const [fin, setFin] = useState<any>(null)
  const [fans, setFans] = useState<any>(null)
  const [saved, setSaved] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => {
    if (!q.data) return
    const f = q.data.finance
    setFin({ agency: f.agency_commission_pct ?? '', chatter: f.chatter_commission_pct ?? '', other: f.other_monthly_costs_cents != null ? f.other_monthly_costs_cents / 100 : '', base: f.commission_base })
    const t = q.data.fans
    setFans({ vip: t.vip_cents / 100, high: t.high_value_cents / 100, new_days: t.new_days, active: t.at_risk_active_days, lookback: t.at_risk_lookback_days })
  }, [q.data])
  if (q.isLoading || !fin || !fans) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} />
  const n = (v: any) => v === '' || v === null ? null : Number(v)
  const save = async (which: 'finance' | 'fans') => {
    setErr(''); setSaved('')
    try {
      if (which === 'finance') await apiSend('PUT', '/settings/finance', { agency_commission_pct: n(fin.agency), chatter_commission_pct: n(fin.chatter), other_monthly_costs_cents: fin.other === '' ? null : Math.round(Number(fin.other) * 100), commission_base: fin.base })
      else await apiSend('PUT', '/settings/fans', { vip_cents: Math.round(fans.vip * 100), high_value_cents: Math.round(fans.high * 100), new_days: Number(fans.new_days), at_risk_active_days: Number(fans.active), at_risk_lookback_days: Number(fans.lookback) })
      setSaved(which); qc.invalidateQueries()
    } catch (e: any) { setErr(e.message) }
  }

  return (
    <div className="max-w-4xl">
      <PageHeader title="Settings" subtitle="Local business rules. Stored in this dashboard's database only — never sent to Infloww." />
      <div className="mb-4 flex items-start gap-3 rounded-xl border border-good/25 bg-good/5 p-4 text-[13px] text-ink-2">
        <ShieldCheck size={18} className="mt-0.5 shrink-0 text-good" />
        <div>Infloww access is <b>read-only</b>: the backend can only send GET requests to an allowlist of documented endpoints. The API key lives in the backend environment and is never sent to this browser. Nothing on this page changes anything in Infloww.</div>
      </div>
      {err && <div className="mb-3 text-sm text-bad">{err}</div>}
      <Card title="Financial estimates" subtitle="Infloww has no data on your commission deals or payroll. These rules power the estimates on the Revenue page.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Agency commission (%)" hint="Share of creator revenue the agency keeps. Leave blank to hide profit estimates."><input className="input mt-1 w-full" inputMode="decimal" value={fin.agency} onChange={e => setFin({ ...fin, agency: e.target.value })} placeholder="e.g. 40" /></Field>
          <Field label="Commission base"><select className="input mt-1 w-full" value={fin.base} onChange={e => setFin({ ...fin, base: e.target.value })}><option value="net">Net revenue (after OnlyFans fee)</option><option value="gross">Gross revenue</option></select></Field>
          <Field label="Chatter commission (% of attributed sales)" hint="Used to estimate chatter pay. Infloww exposes no payroll."><input className="input mt-1 w-full" inputMode="decimal" value={fin.chatter} onChange={e => setFin({ ...fin, chatter: e.target.value })} placeholder="e.g. 8" /></Field>
          <Field label="Other operating costs per month" hint="Pro-rated over the selected range (tools, salaries, Infloww plan…)."><input className="input mt-1 w-full" inputMode="decimal" value={fin.other} onChange={e => setFin({ ...fin, other: e.target.value })} placeholder="e.g. 2500" /></Field>
        </div>
        <div className="mt-4 flex items-center gap-3"><button className="btn-primary" onClick={() => save('finance')}>Save financial rules</button>{saved === 'finance' && <span className="flex items-center gap-1 text-xs text-good"><Check size={13} />Saved</span>}</div>
      </Card>

      <Card className="mt-4" title="Fan segmentation thresholds" subtitle="Transparent rules applied to spend over the synced history window.">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="VIP: spend at least" hint={money(fans.vip * 100)}><input className="input mt-1 w-full" inputMode="decimal" value={fans.vip} onChange={e => setFans({ ...fans, vip: e.target.value })} /></Field>
          <Field label="High value: spend at least" hint={money(fans.high * 100)}><input className="input mt-1 w-full" inputMode="decimal" value={fans.high} onChange={e => setFans({ ...fans, high: e.target.value })} /></Field>
          <Field label="'New' = first purchase within (days)"><input className="input mt-1 w-full" inputMode="numeric" value={fans.new_days} onChange={e => setFans({ ...fans, new_days: e.target.value })} /></Field>
          <Field label="'At risk' = no purchase for (days)"><input className="input mt-1 w-full" inputMode="numeric" value={fans.active} onChange={e => setFans({ ...fans, active: e.target.value })} /></Field>
          <Field label="…but purchased within (days)" hint="Requires at least this much synced history, otherwise At Risk is not assigned."><input className="input mt-1 w-full" inputMode="numeric" value={fans.lookback} onChange={e => setFans({ ...fans, lookback: e.target.value })} /></Field>
        </div>
        <div className="mt-4 flex items-center gap-3"><button className="btn-primary" onClick={() => save('fans')}>Save thresholds</button>{saved === 'fans' && <span className="flex items-center gap-1 text-xs text-good"><Check size={13} />Saved</span>}</div>
      </Card>

      <Card className="mt-4" title="Campaign costs" subtitle="Entered per link on the Marketing page.">
        {q.data.campaign_costs.length ? (
          <table className="w-full text-[13px]"><thead><tr className="text-[11px] text-ink-3 uppercase"><th className="pb-2 text-left font-medium">Link</th><th className="pb-2 text-right font-medium">Cost</th><th className="pb-2 text-right font-medium">Spend date</th><th className="pb-2 text-left pl-4 font-medium">Note</th></tr></thead>
            <tbody>{q.data.campaign_costs.map((c: any) => <tr key={c.link_type + c.link_id} className="border-t border-line/60"><td className="py-1.5">{c.link_type} #{c.link_id}</td><td className="text-right tabular">{money(c.cost_cents)}</td><td className="text-right">{c.spent_on || <span className="text-warn">undated</span>}</td><td className="pl-4 text-ink-3">{c.note}</td></tr>)}</tbody></table>
        ) : <div className="text-sm text-ink-3">No costs entered yet.</div>}
      </Card>

      <Photos />

      <Card className="mt-4" title="This browser session">
        <div className="flex items-center justify-between text-[13px]"><span className="text-ink-2">Dashboard access token: {getToken() ? 'set for this tab' : 'not set (backend has no token, or not required)'}</span>
          {getToken() && <button className="btn" onClick={() => { setToken(''); location.reload() }}>Sign out</button>}</div>
      </Card>
    </div>
  )
}
