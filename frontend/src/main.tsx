import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// The standalone HTML build opens from file://, where only hash routes work.
const Router = import.meta.env.VITE_STATIC ? HashRouter : BrowserRouter
const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: (n, e: any) => e?.status !== 401 && n < 1, refetchOnWindowFocus: false } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </Router>
    </QueryClientProvider>
  </StrictMode>,
)
