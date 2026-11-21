import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, CircleDashed, Loader2, PlugZap, RefreshCw, XCircle } from 'lucide-react'
import { DataTable } from '../components/DataTable'
import { Badge, Card, Empty, ErrorState, Kpi, PageHeader, PageSkeleton } from '../components/ui'
import { apiGet, apiSend } from '../lib/api'
import { ago, num, tsTime } from '../lib/format'

export default function Status() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['status'], queryFn: () => apiGet('/status'), refetchInterval: 5000 })
  const probe = useMutation({ mutationFn: () => apiGet('/health/infloww') })
  const sync = useMutation({ mutationFn: () => apiSend('POST', '/sync', { include_links: true, force_reference: true }), onSuccess: () => qc.invalidateQueries() })
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const eps: any[] = d.endpoints
  const called = eps.filter(e => e.calls)
  const lastOk = Math.max(0, ...eps.map(e => e.last_success || 0))
  const lastFail = Math.max(0, ...eps.map(e => e.last_failure || 0))
  const authErr = eps.reduce((a, e) => a + (e.auth_errors || 0), 0)
  const rlErr = eps.reduce((a, e) => a + (e.rate_limit_errors || 0), 0)
  const running = d.jobs.find((j: any) => !j.finished)

  return (
    <div>
      <PageHeader title="API status & data quality" subtitle="Connectivity, freshness and completeness of everything shown in this dashboard."
        actions={<>
          <button className="btn" onClick={() => probe.mutate()} disabled={probe.isPending}>{probe.isPending ? <Loader2 size={14} className="animate-spin" /> : <PlugZap size={14} />}Test connection</button>
          <button className="btn-primary" onClick={() => sync.mutate()} disabled={sync.isPending || !!running || !d.configured}><RefreshCw size={14} className={running ? 'animate-spin' : ''} />{running ? `Syncing ${running.done}/${running.total || '…'}` : 'Sync now'}</button>
        </>} />
      {probe.data && (
        <div className={`mb-4 rounded-xl border p-3 text-sm ${probe.data.status === 'ok' ? 'border-good/30 bg-good/5 text-good' : 'border-bad/30 bg-bad/5 text-bad'}`}>
          {probe.data.status === 'ok' ? `Connected — Infloww returned ${probe.data.has_business_data ? 'creator data' : 'an empty creator list (check the key\'s creator scope)'} in ${probe.data.ms} ms.`
            : probe.data.status === 'not_configured' ? probe.data.detail : `Connection failed: ${probe.data.error?.kind} — ${probe.data.error?.message}${probe.data.error?.request_id ? ` (x-request-id ${probe.data.error.request_id})` : ''}`}
        </div>
      )}
      {sync.error && <div className="mb-4 text-sm text-bad">{(sync.error as Error).message}</div>}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Kpi label="Configuration" value={d.configured ? 'Configured' : 'Missing'} sub={<span>OID {d.agency_oid || '—'} · arrays: {d.array_style}</span>} />
        <Kpi label="Last successful call" value={lastOk ? ago(lastOk) : 'never'} sub={<span>{tsTime(lastOk || null)}</span>} />
        <Kpi label="Last failed call" value={lastFail ? ago(lastFail) : 'none'} sub={<span>{tsTime(lastFail || null)}</span>} />
        <Kpi label="Auth / rate-limit errors" value={`${authErr} / ${rlErr}`} sub={<span>since server start · budget {d.qpm_budget} QPM</span>} />
      </div>

      <Card className="mt-4" title="Data coverage — default window" subtitle={`${d.coverage_default_window.start} → ${d.coverage_default_window.end} (UTC). Each unit is one creator- or employee-day fully synced.`}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {d.coverage_default_window.items.map((c: any) => {
            const ratio = c.expected ? c.covered / c.expected : 0
            return (
              <div key={c.dataset} className="rounded-xl border border-line bg-bg/40 p-3">
                <div className="flex items-center justify-between text-[13px] font-medium">{c.dataset}{c.complete ? <CheckCircle2 size={15} className="text-good" /> : <CircleDashed size={15} className="text-warn" />}</div>
                <div className="mt-2 h-1.5 rounded-full bg-ink/5"><div className="h-1.5 rounded-full" style={{ width: `${ratio * 100}%`, background: c.complete ? '#22c55e' : '#fab219' }} /></div>
                <div className="mt-1.5 flex justify-between text-[11px] text-ink-3 tabular"><span>{num(c.covered)}/{num(c.expected)}</span><span>oldest fetch {ago(c.oldest_fetch)}</span></div>
              </div>)
          })}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:grid-cols-6">
          {Object.entries(d.record_counts).map(([k, v]) => <div key={k} className="rounded-lg bg-ink/[0.03] px-2.5 py-1.5"><div className="text-ink-3">{k}</div><div className="font-medium tabular">{num(v as number)}</div></div>)}
        </div>
      </Card>

      <Card className="mt-4" title="Endpoint health" subtitle="Every Infloww endpoint in the read-only allowlist (all GET)">
        <DataTable rows={eps} rowKey={r => r.path} pageSize={30} dense initialSort={{ key: 'calls', dir: 'desc' }} columns={[
          { key: 'path', label: 'Endpoint', render: r => <span className="font-mono text-[12px]">{r.path}</span> },
          { key: 'state', label: 'State', value: r => r.last_failure && (!r.last_success || r.last_failure > r.last_success) ? 0 : r.calls ? 2 : 1, render: r =>
            !r.calls ? <Badge>not called yet</Badge> : r.last_failure && (!r.last_success || r.last_failure > r.last_success) ? <Badge tone="bad" title={r.last_error}><XCircle size={11} />{r.last_error_kind}</Badge> : <Badge tone="good"><CheckCircle2 size={11} />ok</Badge> },
          { key: 'calls', label: 'Calls', align: 'right', render: r => num(r.calls) },
          { key: 'failures', label: 'Fails', align: 'right', render: r => r.failures ? <span className="text-bad">{r.failures}</span> : '0' },
          { key: 'records', label: 'Records', align: 'right', hideBelow: 'md', render: r => num(r.records) },
          { key: 'avg_ms', label: 'Avg ms', align: 'right', hideBelow: 'md', render: r => num(r.avg_ms) },
          { key: 'p95_ms', label: 'p95 ms', align: 'right', hideBelow: 'lg', render: r => num(r.p95_ms) },
          { key: 'pages_incomplete', label: 'Paging errs', align: 'right', hideBelow: 'lg', render: r => r.pages_incomplete ? <span className="text-bad">{r.pages_incomplete}</span> : '0' },
          { key: 'last_success', label: 'Last OK', align: 'right', hideBelow: 'md', render: r => ago(r.last_success) },
          { key: 'latency_note', label: 'Upstream delay', hideBelow: 'lg', render: r => <span className="text-ink-3">{r.latency_note || '—'}</span> },
        ]} />
        <div className="mt-2 text-[11px] text-ink-3">{called.length} of {eps.length} endpoints exercised since the server started.</div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Unsupported / unavailable metrics" subtitle="What the dashboard deliberately does not fabricate">
          <ul className="space-y-2 text-[13px]">{d.unsupported_metrics.map((u: any) => <li key={u.metric}><div className="font-medium">{u.metric}</div><div className="text-xs text-ink-3">{u.reason}</div></li>)}
            {Object.entries(d.capabilities).filter(([, c]: any) => !c.available).map(([k, c]: any) => <li key={k}><div className="font-medium text-bad">{k}</div><div className="text-xs text-ink-3">{c.reason}</div></li>)}</ul>
        </Card>
        <Card title="Recent sync errors">
          {d.sync_errors.length ? <DataTable rows={d.sync_errors} rowKey={r => r.ts + r.dataset + r.scope} pageSize={8} dense columns={[
            { key: 'ts', label: 'When', render: r => ago(r.ts) }, { key: 'dataset', label: 'Dataset' }, { key: 'scope', label: 'Scope' },
            { key: 'kind', label: 'Kind', render: r => <Badge tone="bad">{r.kind}</Badge> }, { key: 'message', label: 'Message', render: r => <span className="block max-w-72 truncate text-ink-3" title={r.message}>{r.message}</span> }]} />
            : <Empty title="No sync errors in the last 7 days" icon={<CheckCircle2 size={20} className="text-good" />} />}
        </Card>
      </div>

      <Card className="mt-4" title="Recent API calls" subtitle="Sanitised — no credentials or headers are ever recorded">
        <DataTable rows={d.recent_calls} rowKey={r => r.ts + r.path + r.attempt + JSON.stringify(r.params)} pageSize={12} dense columns={[
          { key: 'ts', label: 'Time', render: r => tsTime(r.ts) }, { key: 'path', label: 'Endpoint', render: r => <span className="font-mono text-[12px]">GET {r.path}</span> },
          { key: 'status', label: 'Status', align: 'right', render: r => <span className={r.status === 200 ? 'text-good' : 'text-bad'}>{r.status ?? r.error_kind}</span> },
          { key: 'records', label: 'Rows', align: 'right', render: r => num(r.records) }, { key: 'duration_ms', label: 'ms', align: 'right', render: r => num(r.duration_ms) },
          { key: 'request_id', label: 'x-request-id', hideBelow: 'lg', render: r => <span className="font-mono text-[11px] text-ink-3">{r.request_id || '—'}</span> },
        ]} />
      </Card>
    </div>
  )
}
