import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiGet, type Params } from './api'
import { useFilters } from './filters'

/** Fetch a dashboard endpoint scoped by the global filters. Polls while the backend reports a sync in progress. */
export function useDash<T = any>(path: string, extra?: Params, opts: { enabled?: boolean; useFilters?: boolean } = {}) {
  const f = useFilters()
  const params = { ...(opts.useFilters === false ? {} : f.params), ...(extra || {}) }
  return useQuery<T>({
    queryKey: [path, params],
    queryFn: () => apiGet<T>(path, params),
    placeholderData: keepPreviousData,
    enabled: opts.enabled !== false,
    refetchInterval: q => ((q.state.data as any)?.meta?.syncing ? 4000 : false),
  })
}

export function useMeta() {
  return useQuery<any>({ queryKey: ['meta'], queryFn: () => apiGet('/meta'), refetchInterval: q => ((q.state.data as any)?.syncing ? 5000 : 60000) })
}
