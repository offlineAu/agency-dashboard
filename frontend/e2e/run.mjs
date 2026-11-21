// Browser regression suite (Playwright library). Run against backend fixture server + vite dev:
//   backend: .venv/bin/python -m scripts.fixture_server     frontend: npm run dev     then: npm run e2e
import { chromium, devices } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE = process.env.E2E_BASE_URL || 'http://localhost:5173'
const PAGES = [
  ['/', /Agency overview/], ['/creators', /^Creators$/], ['/creators/1000', /Creator A/], ['/creators/compare?ids=1000,1001,1002', /Creator comparison/],
  ['/chatters', /^Chatters$/], ['/chatters/70', /Chatter 1/], ['/fans', /Fan intelligence/], ['/revenue', /Revenue & financials/],
  ['/marketing', /Marketing & promotion/], ['/analytics', /Message analytics/], ['/reports', /^Reports$/], ['/status', /API status/], ['/settings', /^Settings$/],
]
mkdirSync('e2e/screens', { recursive: true })
let pass = 0, fail = 0
const results = []
async function check(name, fn) {
  try { await fn(); pass++; results.push(`  ✓ ${name}`) } catch (e) { fail++; results.push(`  ✗ ${name}\n      ${String(e.message || e).split('\n').slice(0, 4).join('\n      ')}`) }
}
const assert = (c, m) => { if (!c) throw new Error(m) }

const browser = await chromium.launch()
for (const [label, ctxOpts] of [['desktop', { viewport: { width: 1440, height: 900 } }], ['mobile', { ...devices['Pixel 7'] }]]) {
  const ctx = await browser.newContext(ctxOpts)
  for (const [path, heading] of PAGES) {
    await check(`${label} renders ${path}`, async () => {
      const page = await ctx.newPage()
      const errors = [], external = []
      page.on('pageerror', e => errors.push(e.message))
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
      page.on('request', r => { if (/infloww\.com/.test(r.url())) external.push(r.url()) })
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded' })
      await page.locator('h1').first().waitFor({ timeout: 15000 })
      await page.waitForTimeout(1500)
      const h1 = await page.locator('h1').first().innerText()
      assert(heading.test(h1), `heading "${h1}" !~ ${heading}`)
      assert(await page.getByText("Couldn't load this view").count() === 0, 'error state shown')
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      assert(overflow <= 1, `horizontal overflow ${overflow}px`)
      assert(!errors.length, 'console errors: ' + errors.join(' | '))
      assert(!external.length, 'browser called Infloww directly')
      await page.screenshot({ path: `e2e/screens/${label}${path.replace(/[/?=,]/g, '_')}.png`, fullPage: true })
      await page.close()
    })
  }
  await ctx.close()
}

const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true })
const page = await ctx.newPage()
await check('date filter changes the data and URL', async () => {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  const kpi = page.getByTestId('hero-revenue')
  await kpi.waitFor()
  await page.waitForTimeout(800)
  const before = await kpi.innerText()
  await page.getByRole('button', { name: /Last 30 days/ }).click()
  await page.getByRole('button', { name: 'Last 7 days', exact: true }).click()
  await page.waitForURL(/range=7d/)
  await page.waitForTimeout(1500)
  assert((await kpi.innerText()) !== before, 'KPI unchanged after date change')
})
await check('gross/net toggle + creator filter propagate across pages', async () => {
  await page.goto(BASE + '/creators', { waitUntil: 'domcontentloaded' })
  await page.getByRole('tab', { name: 'Net' }).click()
  await page.waitForURL(/basis=net/)
  await page.getByRole('columnheader', { name: /Net revenue/ }).waitFor()
  await page.getByRole('button', { name: /All creators/ }).click()
  await page.getByRole('button', { name: 'Creator B', exact: true }).click()
  await page.waitForURL(/creators=1001/)
  await page.keyboard.press('Escape')
  await page.getByRole('link', { name: 'Chatters' }).first().click()
  await page.waitForURL(/\/chatters\?/)
  assert(/basis=net/.test(page.url()) && /creators=1001/.test(page.url()), 'filters lost on navigation: ' + page.url())
})
await check('table search filters rows', async () => {
  await page.goto(BASE + '/chatters', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('Search table').fill('Chatter 3')
  await page.waitForTimeout(300)
  const n = await page.locator('table').first().locator('tbody tr', { hasText: 'Chatter' }).count()
  assert(n === 1, `expected 1 row, got ${n}`)
})
await check('campaign cost entry produces ROI', async () => {
  await page.goto(BASE + '/marketing', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Edit cost for TikTok promo/ }).first().click()
  await page.getByRole('dialog').getByRole('textbox').first().fill('1000')
  await page.getByRole('button', { name: 'Save' }).click()
  await page.getByRole('dialog').waitFor({ state: 'detached' })
  await page.waitForTimeout(1000)
  assert(await page.getByText('Add link costs to compute ROI').count() === 0, 'ROI still unavailable')
})
await check('theme toggle switches to dark and persists across reload', async () => {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Switch to dark theme/ }).click()
  assert(await page.evaluate(() => document.documentElement.dataset.theme) === 'dark', 'not dark after toggle')
  await page.reload({ waitUntil: 'domcontentloaded' })
  assert(await page.evaluate(() => document.documentElement.dataset.theme) === 'dark', 'theme not persisted')
  await page.getByRole('button', { name: /Switch to light theme/ }).click()
  assert(await page.evaluate(() => document.documentElement.dataset.theme) === 'light', 'not light after toggle back')
})
await check('quick search jumps to a creator', async () => {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  const box = page.getByRole('textbox', { name: /Search creators, chatters and pages/ })
  await box.fill('Creator A')
  await box.press('Enter')
  await page.waitForURL(/\/creators\/\d+/)
})
await check('CSV / XLSX / PDF exports download', async () => {
  await page.goto(BASE + '/reports', { waitUntil: 'domcontentloaded' })
  for (const [btn, ext] of [['CSV', 'csv'], ['Excel', 'xlsx'], ['PDF', 'pdf']]) {
    const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: btn, exact: true }).click()])
    assert(new RegExp(`^daily_.*\\.${ext}$`).test(dl.suggestedFilename()), 'bad filename ' + dl.suggestedFilename())
  }
})
await check('mobile navigation drawer opens and navigates', async () => {
  const m = await browser.newContext({ ...devices['Pixel 7'] })
  const p = await m.newPage()
  await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await p.getByLabel('Open navigation').click()
  await p.getByRole('link', { name: 'Fans' }).click()
  await p.waitForURL(/\/fans/)
  await m.close()
})
await browser.close()
console.log(results.join('\n'))
console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
