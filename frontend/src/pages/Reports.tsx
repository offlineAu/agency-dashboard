import { Download, FileSpreadsheet, FileText, Loader2, Table2 } from 'lucide-react'
import { useState } from 'react'
import { Card, ErrorState, PageHeader } from '../components/ui'
import { download } from '../lib/api'
import { useFilters } from '../lib/filters'
import { money, num, pct } from '../lib/format'
import { useDash } from '../lib/hooks'

const REPORTS = [
  ['daily', 'Daily revenue report', 'Revenue per UTC day by source'], ['weekly', 'Weekly performance report', 'Revenue per ISO week'],
  ['monthly', 'Monthly agency report', 'Revenue per calendar month'], ['creators', 'Creator comparison report', 'Revenue, growth, audience per creator'],
  ['employees', 'Chatter performance report', 'Attributed sales and chat KPIs'], ['fans', 'Fan spending report', 'Top 500 fans, pseudonymised'],
  ['campaigns', 'Campaign ROI report', 'Links with earnings, costs and ROI'], ['revenue-sources', 'Revenue source report', 'Gross/net by transaction type'],
] as const

export default function Reports() {
  const f = useFilters()
  const [kind, setKind] = useState<string>('daily')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const q = useDash(`/reports/${kind}`)
  const exp = async (fmt: string) => {
    setBusy(fmt); setErr('')
    try { await download(`/reports/${kind}`, { ...f.params, format: fmt }, `${kind}_${f.start}_${f.end}.${fmt}`) } catch (e: any) { setErr(e.message) } finally { setBusy('') }
  }
  const fmtCell = (v: any, k: string) => v == null || v === '' ? '—' : k === 'money' ? money(v) : k === 'pct' ? pct(v) : k === 'num' ? num(v, 2) : String(v)
  return (
    <div>
      <PageHeader title="Reports" subtitle="Every export uses the same calculations as the dashboard and respects the filters above." meta={q.data?.meta} />
      <div className="grid gap-4 lg:grid-cols-4">
        <Card title="Report type" className="lg:col-span-1" pad={false}>
          <ul className="p-2">{REPORTS.map(([k, t, s]) => (
            <li key={k}><button onClick={() => setKind(k)} className={`w-full rounded-lg px-3 py-2 text-left ${kind === k ? 'bg-accent/15 ring-1 ring-accent/30' : 'hover:bg-ink/[0.03]'}`}>
              <div className="text-[13px] font-medium">{t}</div><div className="text-[11px] text-ink-3">{s}</div></button></li>))}</ul>
        </Card>
        <div className="space-y-4 lg:col-span-3">
          <Card title={q.data?.title || 'Report'} action={
            <div className="flex flex-wrap gap-2">
              <button className="btn" onClick={() => exp('csv')} disabled={!!busy}>{busy === 'csv' ? <Loader2 size={14} className="animate-spin" /> : <Table2 size={14} />}CSV</button>
              <button className="btn" onClick={() => exp('xlsx')} disabled={!!busy}>{busy === 'xlsx' ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />}Excel</button>
              <button className="btn-primary" onClick={() => exp('pdf')} disabled={!!busy}>{busy === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}PDF</button>
            </div>}>
            {err && <div className="mb-3 text-xs text-bad">{err}</div>}
            {q.error ? <ErrorState error={q.error} /> : !q.data ? <div className="skeleton h-64" /> : (
              <>
                <dl className="mb-4 grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">{q.data.header.slice(1).map(([k, v]: string[]) => (
                  <div key={k} className="flex gap-2"><dt className="w-28 shrink-0 text-ink-3">{k}</dt><dd className={k === 'Coverage' && v !== 'complete' ? 'text-warn' : 'text-ink-2'}>{v}</dd></div>))}</dl>
                <div className={`-mx-5 max-h-[520px] overflow-auto px-5 ${q.isFetching ? 'opacity-60' : ''}`}>
                  <table className="w-full text-[12.5px]">
                    <thead><tr>{q.data.columns.map(([k, l, t]: string[]) => <th key={k} className={`sticky top-0 border-b border-line bg-card px-2 py-2 text-[11px] font-medium whitespace-nowrap text-ink-3 uppercase ${t === 'text' ? 'text-left' : 'text-right'}`}>{l}</th>)}</tr></thead>
                    <tbody>
                      {q.data.rows.slice(0, 300).map((r: any, i: number) => <tr key={i} className="border-b border-line/50">{q.data.columns.map(([k, , t]: string[]) => <td key={k} className={`px-2 py-1.5 whitespace-nowrap ${t === 'text' ? '' : 'text-right tabular'}`}>{fmtCell(r[k], t)}</td>)}</tr>)}
                      {q.data.totals && <tr className="font-semibold">{q.data.columns.map(([k, , t]: string[]) => <td key={k} className={`border-t border-line-2 px-2 py-2 ${t === 'text' ? '' : 'text-right tabular'}`}>{fmtCell(q.data.totals[k], t)}</td>)}</tr>}
                    </tbody>
                  </table>
                  {q.data.rows.length > 300 && <div className="py-2 text-center text-xs text-ink-3">Preview shows 300 of {q.data.rows.length} rows — exports include all.</div>}
                </div>
                <ul className="mt-4 list-disc space-y-0.5 pl-5 text-xs text-ink-3">{q.data.definitions.map((d: string, i: number) => <li key={i}>{d}</li>)}</ul>
              </>
            )}
          </Card>
          <p className="flex items-center gap-1.5 text-xs text-ink-3"><Download size={12} />Exports include agency identifier, period, generation time (UTC), filters, data coverage and metric definitions.</p>
        </div>
      </div>
    </div>
  )
}
