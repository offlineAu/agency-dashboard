// Build the dashboard as ONE self-contained HTML file that runs from disk with no backend:
// the app bundle and CSS are inlined, and /api requests are answered from a captured snapshot.
//   node scripts/build-static.mjs <snapshot.json> <out.html>
// The output contains real agency data: keep it private and out of git.
import { execSync } from 'node:child_process'
import { readFileSync, writeFileSync, readdirSync, rmSync } from 'node:fs'

const [snapPath, outPath] = process.argv.slice(2)
if (!snapPath || !outPath) throw new Error('usage: build-static.mjs <snapshot.json> <out.html>')
const snap = JSON.parse(readFileSync(snapPath, 'utf8'))

rmSync('dist-static', { recursive: true, force: true })
execSync('npx vite build --outDir dist-static --emptyOutDir', { stdio: 'inherit', env: { ...process.env, VITE_STATIC: '1' } })
const assets = readdirSync('dist-static/assets')
const js = assets.filter(f => f.endsWith('.js')), css = assets.filter(f => f.endsWith('.css'))
if (js.length !== 1) throw new Error('expected a single JS bundle, got ' + js.join(', '))

const safe = s => s.replace(/<\/(script)/gi, '<\\/$1').replace(/<!--/g, '<\\!--')
const captured = new Date(snap.captured_at)
const label = captured.toLocaleString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' UTC'

const shim = `
window.__SNAPSHOT_TODAY__ = ${JSON.stringify(snap.today + 'T12:00:00Z')};
(function () {
  var S = JSON.parse(document.getElementById('snapshot-data').textContent);
  var realFetch = window.fetch.bind(window);
  function key(u) {
    var x = new URL(u, 'http://snapshot.local'); var q = Array.from(x.searchParams.entries()).sort(function (a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0 });
    return x.pathname + (q.length ? '?' + new URLSearchParams(q).toString() : '');
  }
  function reply(status, body) { return Promise.resolve(new Response(JSON.stringify(body), { status: status, headers: { 'Content-Type': 'application/json' } })) }
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : input.url;
    if (!/^\\/api\\//.test(url)) return realFetch(input, init);
    var method = ((init && init.method) || 'GET').toUpperCase();
    if (method !== 'GET') return reply(403, { detail: 'This is a read-only snapshot. Changes can only be made on the live dashboard.' });
    var i = S.keys[key(url)]; var hit = i === undefined ? undefined : S.bodies[i];
    if (!hit) return reply(404, { detail: 'This view isn\\'t included in the snapshot. Try another date range, or open the live dashboard.' });
    var body = JSON.parse(JSON.stringify(hit)); var m = S.metas[key(url)]; if (m) body = Object.assign({ meta: JSON.parse(JSON.stringify(m)) }, body);
    if (body && typeof body === 'object') { if ('syncing' in body) body.syncing = false; if (body.meta && typeof body.meta === 'object') body.meta.syncing = false }
    return reply(200, body);
  };
  document.addEventListener('DOMContentLoaded', function () {
    var b = document.createElement('div');
    b.textContent = 'Snapshot · ' + ${JSON.stringify(label)};
    b.title = 'A saved copy of the dashboard. Data is frozen at this time and filters are limited to the presets that were captured.';
    b.style.cssText = 'position:fixed;right:max(12px,env(safe-area-inset-right,0px));bottom:max(12px,env(safe-area-inset-bottom,0px));z-index:9999;font:600 12px/1 Inter,system-ui,sans-serif;padding:8px 12px;border-radius:999px;background:#101828;color:#fff;opacity:.88;pointer-events:auto;box-shadow:0 6px 18px -6px rgba(0,0,0,.4)';
    document.body.appendChild(b);
  });
})();`

// Store each distinct body once (e.g. lifetime campaign data is identical for every date range).
const bodies = [], seen = new Map(), keys = {}
// `meta` (range, freshness) differs per request, so it is stored per key and the rest shared.
const metas = {}
for (const [k, v] of Object.entries(snap.responses)) {
  let rest = v
  if (v && typeof v === 'object' && !Array.isArray(v) && 'meta' in v) { const { meta, ...r } = v; metas[k] = meta; rest = r }
  const t = JSON.stringify(rest); if (!seen.has(t)) { seen.set(t, bodies.length); bodies.push(rest) } keys[k] = seen.get(t)
}
const packed = { keys, bodies, metas }
let html = readFileSync('dist-static/index.html', 'utf8')
html = html.replace(/<script type="module"[^>]*src="[^"]+"[^>]*><\/script>\s*/g, '')
html = html.replace(/<link rel="stylesheet"[^>]*href="\/assets\/[^"]+"[^>]*>\s*/g, '')
const head = `<meta name="snapshot-captured" content="${snap.captured_at}" />
    <style>${css.map(f => readFileSync('dist-static/assets/' + f, 'utf8')).join('\n')}</style>
    <script type="application/json" id="snapshot-data">${safe(JSON.stringify(packed))}</script>
    <script>${safe(shim)}</script>
  </head>`
html = html.replace('</head>', () => head) // function form: the data may contain $' / $& patterns
const app = `<script type="module">${safe(readFileSync('dist-static/assets/' + js[0], 'utf8'))}</script>\n  </body>`
html = html.replace('</body>', () => app)
writeFileSync(outPath, html)
rmSync('dist-static', { recursive: true, force: true })
console.log(`${outPath}: ${(html.length / 1048576).toFixed(1)} MB, ${Object.keys(snap.responses).length} API responses, captured ${label}`)
