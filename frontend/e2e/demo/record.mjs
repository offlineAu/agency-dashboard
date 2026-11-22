// Frame-accurate narrated demo recorder.
//   DEMO_TOKEN=... DEMO_URL=https://... DEMO_OUT=/path/to/workdir node e2e/demo/record.mjs
// Writes <out>/frames/%06d.jpg (30 fps), <out>/audio/NN.aiff and <out>/timeline.json.
// Every frame sets the scroll position explicitly, so playback is smooth regardless of how
// fast the site renders. Narration uses the built-in macOS `say` (offline; nothing leaves the Mac).
import { chromium } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { SCENES } from './scenes.mjs'

const BASE = process.env.DEMO_URL, TOKEN = process.env.DEMO_TOKEN, OUT = process.env.DEMO_OUT
const VOICE = process.env.DEMO_VOICE || 'Samantha', RATE = process.env.DEMO_RATE || '178'
const FPS = 30, LEAD = 0.5, TAIL = 0.9, SCROLL_S = 1.1, HEADER = 132
if (!BASE || !TOKEN || !OUT) throw new Error('DEMO_URL, DEMO_TOKEN and DEMO_OUT are required')
rmSync(`${OUT}/frames`, { recursive: true, force: true }); mkdirSync(`${OUT}/frames`, { recursive: true }); mkdirSync(`${OUT}/audio`, { recursive: true })

// 1. Narration audio + durations
const timeline = SCENES.map((s, i) => {
  const f = `${OUT}/audio/${String(i).padStart(2, '0')}.aiff`
  execFileSync('say', ['-v', VOICE, '-r', RATE, '-o', f, s.say])
  const secs = Number(/estimated duration: ([\d.]+)/.exec(execFileSync('afinfo', [f]).toString())[1])
  return { audio: f, speech: secs, total: LEAD + secs + TAIL }
})
console.log('narration', timeline.reduce((a, t) => a + t.total, 0).toFixed(1) + 's')

const ease = x => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2
const clamp01 = x => Math.max(0, Math.min(1, x))
const sentences = t => t.match(/[^.!?]+[.!?]+/g)?.map(s => s.trim()) || [t]

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 4 / 3 })
await ctx.addInitScript(t => sessionStorage.setItem('dashboard-token', t), TOKEN)
const page = await ctx.newPage()
const cdp = await ctx.newCDPSession(page)
let frameNo = 0
async function snap() {
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 88 })
  writeFileSync(`${OUT}/frames/${String(frameNo++).padStart(6, '0')}.jpg`, Buffer.from(data, 'base64'))
}

const OVERLAY = () => {
  if (document.getElementById('demo-ov')) return
  const css = document.createElement('style')
  css.textContent = `
    html{scroll-behavior:auto!important}
    #demo-ring{position:fixed;z-index:99998;pointer-events:none;border:3px solid #7c6cff;border-radius:20px;
      box-shadow:0 0 0 9999px rgba(10,14,30,.26),0 0 28px 4px rgba(124,108,255,.55);opacity:0}
    #demo-tag{position:fixed;z-index:99999;pointer-events:none;background:#4f46e5;color:#fff;font:600 15px Inter,system-ui,sans-serif;
      padding:7px 14px;border-radius:999px;box-shadow:0 8px 24px -6px rgba(79,70,229,.6);opacity:0;white-space:nowrap}
    #demo-sub{position:fixed;z-index:99999;left:50%;bottom:28px;transform:translateX(-50%);max-width:980px;width:max-content;
      pointer-events:none;background:rgba(10,14,30,.84);color:#fff;font:500 19px/1.45 Inter,system-ui,sans-serif;
      padding:12px 22px;border-radius:14px;text-align:center;backdrop-filter:blur(6px)}
    #demo-sub:empty{display:none}`
  document.head.appendChild(css)
  for (const id of ['demo-ring', 'demo-tag', 'demo-sub']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d) }
  document.body.appendChild(Object.assign(document.createElement('i'), { id: 'demo-ov' }))
}

// Resolve a beat target to an element; returns its document-space rect.
const LOCATE = ({ target }) => {
  const H = 132
  const cardOf = el => el?.closest('section, .card, [data-testid]') || el
  let el = null
  if (target === 'top') { document.querySelectorAll('[data-demo-target]').forEach(e => e.removeAttribute('data-demo-target')); return { top: 0, el: false } }
  if (target.startsWith('card:') || target.startsWith('text:')) {
    const want = target.slice(5)
    const all = [...document.querySelectorAll('h1,h2,h3,p,span,div,button,a')]
    const hit = all.find(e => e.tagName === 'H2' && e.textContent.trim() === want) ||
                all.find(e => e.children.length === 0 && e.textContent.trim() === want) ||
                all.find(e => e.textContent.trim().startsWith(want) && e.children.length <= 2)
    el = cardOf(hit)
  } else el = document.querySelector(target)
  if (!el) return null
  el.setAttribute('data-demo-target', '1')
  document.querySelectorAll('[data-demo-target]').forEach(e => e !== el && e.removeAttribute('data-demo-target'))
  const r = el.getBoundingClientRect()
  return { top: Math.max(0, r.top + window.scrollY - H - 62), el: true }
}

const FRAME = ({ y, ring, tag, sub, fade }) => {
  window.scrollTo(0, y)
  const R = document.getElementById('demo-ring'), T = document.getElementById('demo-tag'), S = document.getElementById('demo-sub')
  const el = document.querySelector('[data-demo-target]')
  if (el && ring > 0) {
    const r = el.getBoundingClientRect(), p = 8
    const top = Math.max(r.top - p, 118), bottom = Math.min(r.bottom + p, window.innerHeight - 96)
    Object.assign(R.style, { left: r.left - p + 'px', top: top + 'px', width: r.width + 2 * p + 'px', height: Math.max(40, bottom - top) + 'px', opacity: ring })
    T.textContent = tag || ''
    // Above the card when there is room; otherwise inside its top-right corner, clear of the card title.
    const above = top - 44 > 112
    Object.assign(T.style, above ? { left: r.left - p + 'px', right: 'auto', top: top - 44 + 'px' }
      : { left: 'auto', right: window.innerWidth - r.right - p + 14 + 'px', top: top + 14 + 'px' }, { opacity: tag ? ring : 0 })
  } else { R.style.opacity = 0; T.textContent = tag || ''
    Object.assign(T.style, { left: 'auto', right: '40px', top: '150px', opacity: tag ? ring : 0 }) }
  S.textContent = sub
  document.body.style.opacity = fade
}

async function settle() {
  await page.locator('h1').first().waitFor({ timeout: 90000 })
  await page.waitForFunction(() => !document.querySelector('.skeleton'), null, { timeout: 90000 }).catch(() => {})
  await page.waitForTimeout(2600)
}

let topCreatorPath = null, prevPath = null, prevY = 0
for (const [i, scene] of SCENES.entries()) {
  const tl = timeline[i], N = Math.round(tl.total * FPS)
  const subs = sentences(scene.say), totalChars = subs.reduce((a, s) => a + s.length, 0)
  const subAt = t => { // proportional sentence timing across the spoken part
    let acc = LEAD; for (const s of subs) { acc += tl.speech * s.length / totalChars; if (t < acc) return s } return t < LEAD + tl.speech + 0.3 ? subs.at(-1) : '' }

  if (scene.kind === 'title') {
    await page.setContent(`<!doctype html><html><body style="margin:0;height:100vh;display:grid;place-items:center;
      background:radial-gradient(1200px 700px at 20% 10%,#7c6cff 0%,#4f46e5 40%,#1e1b4b 100%);font-family:Inter,system-ui,sans-serif;color:#fff">
      <div style="text-align:center;max-width:1040px;padding:0 40px">
        <div style="margin:0 auto 28px;width:76px;height:76px;border-radius:22px;background:rgba(255,255,255,.16);display:grid;place-items:center">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg></div>
        <h1 style="font-size:64px;letter-spacing:-.02em;margin:0 0 18px">${scene.title}</h1>
        <p style="font-size:24px;line-height:1.5;opacity:.85;margin:0">${scene.sub}</p></div></body></html>`, { waitUntil: 'domcontentloaded' })
    await page.evaluate(OVERLAY)
    for (let f = 0; f < N; f++) {
      const t = f / FPS
      await page.evaluate(FRAME, { y: 0, ring: 0, tag: '', sub: subAt(t), fade: Math.min(clamp01(t / 0.5), clamp01((tl.total - t) / 0.4)) })
      await snap()
    }
    console.log(`scene ${i} title  ${N} frames`); continue
  }

  // page scene
  let path = scene.path
  if (path === '__TOP_CREATOR__') {
    if (!topCreatorPath) {
      await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' }); await settle()
      topCreatorPath = new URL(await page.getByRole('link', { name: /View profile/ }).first().getAttribute('href'), BASE).pathname
    }
    path = topCreatorPath
  }
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' })
  await page.evaluate(t => localStorage.setItem('dashboard-theme', t), scene.dark ? 'dark' : 'light')
  await page.reload({ waitUntil: 'domcontentloaded' }); await settle()
  await page.evaluate(OVERLAY)
  await page.mouse.move(1430, 890)

  // Resolve scroll targets (positions are stable once the page has settled).
  const beats = []
  for (const b of scene.beats) {
    const loc = await page.evaluate(LOCATE, b)
    if (!loc) console.warn(`  ! scene ${i}: target not found: ${b.target}`)
    beats.push({ ...b, top: loc ? loc.top : 0, found: !!loc })
  }
  const maxY = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
  beats.forEach(b => { b.top = Math.min(b.top, maxY) })
  const startY = prevPath === path ? prevY : 0
  const beatLen = tl.total / beats.length

  for (let f = 0; f < N; f++) {
    const t = f / FPS, bi = Math.min(beats.length - 1, Math.floor(t / beatLen)), bt = t - bi * beatLen
    const b = beats[bi], fromY = bi === 0 ? startY : beats[bi - 1].top
    const y = Math.round(fromY + (b.top - fromY) * ease(clamp01(bt / SCROLL_S)))
    const ringIn = clamp01((bt - SCROLL_S * 0.85) / 0.35), ringOut = clamp01((beatLen - bt) / 0.3)
    if (f === 0 || bt * FPS < 1) await page.evaluate(LOCATE, b) // mark the active element
    const sameNext = SCENES[i + 1]?.path === scene.path
    await page.evaluate(FRAME, { y, ring: b.found ? Math.min(ringIn, ringOut) : 0, tag: b.caption, sub: subAt(t),
      fade: Math.min(prevPath === path ? 1 : clamp01(t / 0.35), sameNext ? 1 : clamp01((tl.total - t) / 0.3)) })
    await snap()
  }
  prevPath = path; prevY = beats.at(-1).top
  console.log(`scene ${i} ${path}  ${N} frames  beats ${beats.map(b => (b.found ? '' : '!') + b.target).join(' | ')}`)
}
await browser.close()
writeFileSync(`${OUT}/timeline.json`, JSON.stringify({ fps: FPS, lead: LEAD, scenes: timeline.map(t => ({ audio: t.audio, frames: Math.round(t.total * FPS), lead: LEAD })) }, null, 1))
console.log('frames', frameNo)
