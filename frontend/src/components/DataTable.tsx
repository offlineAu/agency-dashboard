import clsx from 'clsx'
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

export interface Column<T> {
  key: string
  label: ReactNode
  render?: (row: T) => ReactNode
  value?: (row: T) => number | string | null | undefined   // used for sorting & search
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  className?: string
  hideBelow?: 'sm' | 'md' | 'lg'
  title?: string
}

export function DataTable<T = any>({ rows, columns, rowKey, initialSort, pageSize = 15, searchable, searchPlaceholder, onRowClick, empty, dense }: {
  rows: T[]; columns: Column<NoInfer<T>>[]; rowKey: (r: NoInfer<T>) => string; initialSort?: { key: string; dir: 'asc' | 'desc' }; pageSize?: number
  searchable?: boolean; searchPlaceholder?: string; onRowClick?: (r: NoInfer<T>) => void; empty?: ReactNode; dense?: boolean
}) {
  const [sort, setSort] = useState(initialSort)
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)

  const getVal = (c: Column<T>, r: T) => (c.value ? c.value(r) : (r as Record<string, unknown>)[c.key]) as number | string | null | undefined

  const filtered = useMemo(() => {
    let out = rows
    if (q.trim()) {
      const s = q.toLowerCase()
      out = out.filter(r => columns.some(c => { const v = getVal(c, r); return v !== null && v !== undefined && String(v).toLowerCase().includes(s) }))
    }
    if (sort) {
      const c = columns.find(c => c.key === sort.key)
      if (c) {
        out = [...out].sort((a, b) => {
          const va = getVal(c, a), vb = getVal(c, b)
          if (va === null || va === undefined) return 1          // nulls last regardless of direction
          if (vb === null || vb === undefined) return -1
          const cmp = typeof va === 'number' && typeof vb === 'number' ? va - vb : String(va).localeCompare(String(vb))
          return sort.dir === 'asc' ? cmp : -cmp
        })
      }
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, q, sort, columns])

  const pages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const cur = Math.min(page, pages)
  const view = filtered.slice((cur - 1) * pageSize, cur * pageSize)
  const hide = (h?: string) => h === 'sm' ? 'hidden sm:table-cell' : h === 'md' ? 'hidden md:table-cell' : h === 'lg' ? 'hidden lg:table-cell' : ''

  return (
    <div>
      {searchable && (
        <div className="mb-3 flex items-center gap-2">
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-3" />
            <input value={q} onChange={e => { setQ(e.target.value); setPage(1) }} placeholder={searchPlaceholder || 'Search…'} aria-label="Search table"
              className="input w-full pl-8" />
          </div>
          <span className="text-xs text-ink-3 tabular">{filtered.length} row{filtered.length === 1 ? '' : 's'}</span>
        </div>
      )}
      <div className="-mx-5 overflow-x-auto px-5">
        <table className="w-full min-w-full border-separate border-spacing-0 text-[13px]">
          <thead>
            <tr>
              {columns.map(c => {
                const active = sort?.key === c.key
                const canSort = c.sortable !== false
                return (
                  <th key={c.key} title={c.title} scope="col"
                    className={clsx('sticky top-0 border-b border-line bg-card px-3 py-2 text-[11px] font-medium tracking-wide whitespace-nowrap text-ink-3 uppercase first:pl-0 last:pr-0',
                      c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left', hide(c.hideBelow))}>
                    {canSort ? (
                      <button className={clsx('inline-flex items-center gap-1 uppercase hover:text-ink-2', active && 'text-ink')}
                        onClick={() => setSort(s => s?.key === c.key ? { key: c.key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key: c.key, dir: 'desc' })}>
                        {c.label}{active && (sort!.dir === 'desc' ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                      </button>
                    ) : c.label}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {view.map(r => (
              <tr key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined}
                className={clsx('group', onRowClick && 'cursor-pointer')}>
                {columns.map(c => (
                  <td key={c.key} className={clsx('border-b border-line/60 px-3 whitespace-nowrap first:pl-0 last:pr-0 group-hover:bg-ink/[0.02]', dense ? 'py-1.5' : 'py-2.5',
                    c.align === 'right' ? 'text-right tabular' : c.align === 'center' ? 'text-center' : 'text-left', hide(c.hideBelow), c.className)}>
                    {c.render ? c.render(r) : String(getVal(c, r) ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {view.length === 0 && (empty || <div className="py-10 text-center text-sm text-ink-3">No rows match.</div>)}
      </div>
      {pages > 1 && (
        <div className="mt-3 flex items-center justify-end gap-2 text-xs text-ink-3">
          <span className="tabular">Page {cur} of {pages}</span>
          <button className="btn-icon" aria-label="Previous page" disabled={cur <= 1} onClick={() => setPage(cur - 1)}><ChevronLeft size={14} /></button>
          <button className="btn-icon" aria-label="Next page" disabled={cur >= pages} onClick={() => setPage(cur + 1)}><ChevronRight size={14} /></button>
        </div>
      )}
    </div>
  )
}
