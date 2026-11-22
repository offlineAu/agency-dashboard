// Open the standalone HTML from disk and check every page renders from the snapshot.
//   node scripts/test-static.mjs <file.html> [screenshot-dir]
import { chromium } from '@playwright/test'
import { resolve } from 'node:path'

const file = 'file://' + resolve(process.argv[2]), shots = process.argv[3]
const ROUTES = ['/', '/creators', '/chatters', '/fans', '/revenue', '/marketing', '/analytics', '/reports', '/status', '/settings', '/?range=7d', '/revenue?basis=net&range=90d']
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
const errors = [], remote = []
page.on('pageerror', e => errors.push(e.message))
page.on('console', m => m.type() === 'error' && errors.push(m.text()))
page.on('request', r => { const u = r.url(); if (!u.startsWith('file:') && !u.startsWith('data:') && !/fonts\.(googleapis|gstatic)\.com/.test(u)) remote.push(u) })
let fail = 0
const report = (ok, msg) => { if (!ok) fail++; console.log(`${ok ? '✓' : '✗'} ${msg}`) }
for (const r of [...ROUTES, 'DETAIL_CREATOR', 'DETAIL_CHATTER']) {
  let route = r
  if (r === 'DETAIL_CREATOR' || r === 'DETAIL_CHATTER') {
    await page.goto(file + '#' + (r === 'DETAIL_CREATOR' ? '/creators' : '/chatters')); await page.waitForTimeout(1500)
    const kind = r === 'DETAIL_CREATOR' ? 'creators' : 'chatters'
    const ids = await page.evaluate(k => { const S = JSON.parse(document.getElementById('snapshot-data').textContent)
      return Object.keys(S.keys).map(x => (x.match(new RegExp('^/api/' + (k === 'creators' ? 'creators' : 'employees') + '/(\\d+)\\?')) || [])[1]).filter(Boolean) }, kind)
    if (!ids.length) { report(false, `${kind} detail: none in snapshot`); continue }
    route = `/${kind}/${ids[0]}`
  }
  const before = errors.length
  await page.goto(file + '#' + route)
  await page.locator('h1').first().waitFor({ timeout: 15000 }).catch(() => {})
  await page.waitForFunction(() => !document.querySelector('.skeleton'), null, { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(700)
  const h1 = await page.locator('h1').first().innerText().catch(() => '(none)')
  const bad = await page.getByText(/Couldn't load this view|isn't included in the snapshot/).count()
  const newErr = errors.slice(before)
  report(h1 !== '(none)' && !bad && !newErr.length, `${route.padEnd(34)} h1="${h1}"${bad ? ' ERROR-STATE' : ''}${newErr.length ? ' console: ' + newErr[0].slice(0, 120) : ''}`)
  if (shots && ['/', '/marketing', '/chatters'].includes(route)) await page.screenshot({ path: `${shots}/static${route.replace(/\W/g, '_')}.png` })
}
// Unrecorded filters must say so, not show other data.
await page.goto(file + '#/?range=custom&start=2025-01-01&end=2025-01-05'); await page.waitForTimeout(2000)
report(await page.getByText(/isn't included in the snapshot/).count() > 0, 'unrecorded range shows the "not in snapshot" message')
report(await page.getByText(/^Snapshot · /).count() === 1, 'snapshot label visible')
report(!remote.length, 'no network calls besides fonts' + (remote.length ? ': ' + remote.slice(0, 3).join(', ') : ''))
await b.close()
console.log(fail ? `${fail} failed` : 'all passed'); process.exit(fail ? 1 : 0)
