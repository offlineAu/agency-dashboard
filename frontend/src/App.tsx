import { useQueryClient } from '@tanstack/react-query'
import { Lock } from 'lucide-react'
import { lazy, Suspense, useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { PageSkeleton } from './components/ui'
import { apiGet, setToken } from './lib/api'
import { FilterProvider } from './lib/filters'
import Overview from './pages/Overview'

const Creators = lazy(() => import('./pages/Creators'))
const CreatorDetail = lazy(() => import('./pages/CreatorDetail'))
const CreatorCompare = lazy(() => import('./pages/CreatorCompare'))
const Chatters = lazy(() => import('./pages/Chatters'))
const ChatterDetail = lazy(() => import('./pages/ChatterDetail'))
const Fans = lazy(() => import('./pages/Fans'))
const Revenue = lazy(() => import('./pages/Revenue'))
const Marketing = lazy(() => import('./pages/Marketing'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Reports = lazy(() => import('./pages/Reports'))
const Status = lazy(() => import('./pages/Status'))
const SettingsPage = lazy(() => import('./pages/Settings'))

function AuthGate({ children }: { children: React.ReactNode }) {
  const [need, setNeed] = useState(false)
  const [tok, setTok] = useState('')
  const [err, setErr] = useState('')
  const qc = useQueryClient()
  useEffect(() => {
    const h = () => setNeed(true)
    window.addEventListener('dashboard-auth-required', h)
    return () => window.removeEventListener('dashboard-auth-required', h)
  }, [])
  if (!need) return <>{children}</>
  return (
    <div className="grid min-h-full place-items-center p-6">
      <form className="w-full max-w-sm rounded-2xl border border-line bg-card p-6" onSubmit={async e => {
        e.preventDefault(); setToken(tok)
        try { await apiGet('/auth/check'); setNeed(false); setErr(''); qc.invalidateQueries() } catch { setErr('Invalid access token'); setToken('') }
      }}>
        <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Lock size={18} className="text-accent-2" />Dashboard access</div>
        <p className="mb-4 text-sm text-ink-2">This dashboard is protected. Enter the access token configured on the backend (DASHBOARD_ACCESS_TOKEN).</p>
        <input type="password" className="input w-full" value={tok} onChange={e => setTok(e.target.value)} placeholder="Access token" autoFocus aria-label="Access token" />
        {err && <div className="mt-2 text-xs text-bad">{err}</div>}
        <button className="btn-primary mt-4 w-full justify-center" disabled={!tok}>Unlock</button>
        <p className="mt-3 text-[11px] text-ink-3">The token is kept for this browser tab only (sessionStorage).</p>
      </form>
    </div>
  )
}

export default function App() {
  return (
    <AuthGate>
      <FilterProvider>
        <Suspense fallback={<div className="p-6"><PageSkeleton /></div>}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Overview />} />
              <Route path="creators" element={<Creators />} />
              <Route path="creators/compare" element={<CreatorCompare />} />
              <Route path="creators/:id" element={<CreatorDetail />} />
              <Route path="chatters" element={<Chatters />} />
              <Route path="chatters/:id" element={<ChatterDetail />} />
              <Route path="fans" element={<Fans />} />
              <Route path="revenue" element={<Revenue />} />
              <Route path="marketing" element={<Marketing />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="reports" element={<Reports />} />
              <Route path="status" element={<Status />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<div className="py-20 text-center text-ink-3">Page not found.</div>} />
            </Route>
          </Routes>
        </Suspense>
      </FilterProvider>
    </AuthGate>
  )
}
