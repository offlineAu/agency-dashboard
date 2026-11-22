// Record every /api GET response the dashboard makes while visiting each page under the common
// filter presets, for the standalone HTML snapshot.
//   SNAP_URL=https://... SNAP_TOKEN=... SNAP_OUT=snapshot.json node scripts/capture-snapshot.mjs
import { chromium } from '@playwright/test'
import { writeFileSync } from 'node:fs'

const BASE = process.env.SNAP_URL, TOKEN = process.env.SNAP_TOKEN, OUT = process.env.SNAP_OUT
const TOP_CHATTERS = Number(process.env.SNAP_CHATTERS || 30)
if (!BASE || !TOKEN || !OUT) throw new Error('SNAP_URL, SNAP_TOKEN and SNAP_OUT are required')

export const keyOf = u => { const x = new URL(u); const q = [...x.searchParams].sort(([a], [b]) => a.localeCompare(b)); return x.pathname + (q.length ? '?' + new URLSearchParams(q) : '') }
const today = new Date().toISOString().slice(0, 10)
const data = {}
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
await ctx.addInitScript(t => sessionStorage.setItem('dashboard-token', t), TOKEN)
ctx.on('response', async r => {
  const u = r.url()
  if (!u.startsWith(BASE + '/api/') || r.request().method() !== 'GET' || r.status() !== 200) return
  if (!(r.headers()['content-type'] || '').includes('json')) return
  try { data[keyOf(u)] = await r.json() } catch { /* body unavailable */ }
})
const page = await ctx.newPage()
async function visit(path) {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' })
  await page.locator('h1').first().waitFor({ timeout: 90000 }).catch(() => {})
  await page.waitForFunction(() => !document.querySelector('.skeleton'), null, { timeout: 90000 }).catch(() => {})
  await page.waitForTimeout(1200)
}

const VARIANTS = ['', 'range=7d', 'range=90d', 'range=month', 'range=last_month', 'basis=net', 'range=7d&basis=net', 'range=90d&basis=net']
const PAGES = ['/', '/creators', '/chatters', '/fans', '/revenue', '/marketing', '/analytics', '/reports']
for (const p of PAGES) for (const v of VARIANTS) await visit(p + (v ? '?' + v : ''))
for (const p of ['/status', '/settings']) await visit(p)

// Reports: every report type under the default filters.
await visit('/reports')
for (const name of ['Daily revenue report', 'Weekly performance report', 'Monthly agency report', 'Creator comparison report',
  'Chatter performance report', 'Fan spending report', 'Campaign ROI report', 'Revenue source report']) {
  await page.getByText(name, { exact: true }).first().click().catch(() => console.warn('report not found: ' + name))
  await page.waitForTimeout(2500)
}

const metaKey = Object.keys(data).find(k => k === '/api/meta')
const creators = (data[metaKey]?.creators || []).map(c => c.id)
for (const id of creators) for (const v of ['', 'range=7d', 'range=90d', 'basis=net']) await visit(`/creators/${id}` + (v ? '?' + v : ''))
if (creators.length >= 3) await visit(`/creators/compare?ids=${creators.slice(0, 3).join(',')}`)

// Chatters: the top N by attributed sales in the default range (leaderboard order).
const ids = []
const walk = o => { if (Array.isArray(o)) o.forEach(walk); else if (o && typeof o === 'object') { if (o.employee_id && !ids.includes(String(o.employee_id))) ids.push(String(o.employee_id)); Object.values(o).forEach(walk) } }
Object.entries(data).filter(([k]) => k.startsWith('/api/employees?')).forEach(([, v]) => walk(v))
for (const id of ids.slice(0, TOP_CHATTERS)) for (const v of ['', 'range=7d', 'range=90d']) await visit(`/chatters/${id}` + (v ? '?' + v : ''))

await b.close()
writeFileSync(OUT, JSON.stringify({ captured_at: new Date().toISOString(), today, responses: data }))
console.log(`captured ${Object.keys(data).length} responses · ${creators.length} creators · ${Math.min(ids.length, TOP_CHATTERS)} chatters · today=${today}`)
