// Загрузчик: GitHub без моста (context.js) на «поддельном» API GitHub — без браузера.
// Запуск: node gh_harness.js <сценарий>; печатает JSON с результатом. Сценарии — в test_context_github.py.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = path.join(__dirname, '..', '..', 'uploader', 'qa-pro-sfera-uploader', 'context.js');
const scenario = process.argv[2];

/* ---------- поддельный GitHub: ветки → коммиты → деревья ---------- */
const sha = (s) => require('crypto').createHash('sha1').update(String(s)).digest('hex');
const blobs = {}, trees = {}, commits = {}, refs = {};
function mkTree(files) { const t = { sha: sha(JSON.stringify(files) + Math.random()), files: { ...files } }; trees[t.sha] = t; for (const v of Object.values(files)) blobs[sha(v)] = v; return t; }
function mkCommit(tree, parent) { const c = { sha: sha(tree.sha + (parent || '') + Math.random()), tree: tree.sha, parent }; commits[c.sha] = c; return c; }
const base = mkCommit(mkTree({ 'rules/generation.md': 'ПРАВИЛО', 'products/moi/kb/a.md': '# A', 'image.png': 'x', '.github/x.md': 'скрыто' }));
refs.main = base.sha;
const log = [];
let settings = { ghToken: 'tok', ghApi: 'https://api.github.com', ctxGrants: {} };
async function fakeFetch(url, opt = {}) {
  const u = new URL(url), method = opt.method || 'GET';
  log.push(method + ' ' + u.pathname);
  const json = (code, obj) => ({ ok: code < 300, status: code, text: async () => JSON.stringify(obj) });
  if (opt.headers?.Authorization !== 'Bearer tok') return json(401, { message: 'Bad credentials' });
  const p = u.pathname.replace(/^\/repos\/team\/ctx/, '');
  if (p === '') return json(200, { default_branch: 'main', permissions: { push: true } });
  let m;
  if ((m = p.match(/^\/commits\/(.+)$/))) { const c = commits[refs[decodeURIComponent(m[1])]]; return c ? json(200, { sha: c.sha, commit: { tree: { sha: c.tree } } }) : json(404, { message: 'No commit' }); }
  if ((m = p.match(/^\/git\/trees\/([^/]+)$/)) && method === 'GET') { const t = trees[m[1]]; return json(200, { tree: Object.entries(t.files).map(([k, v]) => ({ path: k, type: 'blob', sha: sha(v), size: v.length })), truncated: false }); }
  if ((m = p.match(/^\/git\/blobs\/(.+)$/))) return json(200, { content: Buffer.from(blobs[m[1]], 'utf8').toString('base64') });
  if (p === '/git/trees' && method === 'POST') {
    const b = JSON.parse(opt.body), files = { ...trees[b.base_tree].files };
    for (const x of b.tree) { if (x.sha === null) delete files[x.path]; else files[x.path] = x.content; }
    return json(201, { sha: mkTree(files).sha });
  }
  if (p === '/git/commits' && method === 'POST') { const b = JSON.parse(opt.body); return json(201, { sha: mkCommit(trees[b.tree], b.parents[0]).sha }); }
  if (p === '/git/refs' && method === 'POST') { const b = JSON.parse(opt.body); const name = b.ref.replace('refs/heads/', ''); if (refs[name]) return json(422, { message: 'Reference already exists' }); refs[name] = b.sha; return json(201, {}); }
  if ((m = p.match(/^\/git\/refs\/heads\/(.+)$/)) && method === 'PATCH') { const b = JSON.parse(opt.body); refs[decodeURIComponent(m[1])] = b.sha; return json(200, {}); }
  return json(404, { message: 'Not Found ' + p });
}

/* ---------- окружение фоновой части расширения ---------- */
const asks = [];
const sandbox = {
  console, URL, TextDecoder, Uint8Array, Buffer, setTimeout, clearTimeout,
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  fetch: fakeFetch,
  getSettings: async () => ({ ...settings }),
  saveSettings: async (p) => { settings = { ...settings, ...p }; return settings; },
  bridgeConnect: async () => {}, bridgeSocket: () => null,
  WebSocket: { OPEN: 1 },
  chrome: {
    windows: { create: async ({ url }) => { asks.push(url); return { id: 7 }; }, remove: async () => {}, onRemoved: { addListener: () => {} } },
    storage: { session: { _d: {}, async set(o) { Object.assign(this._d, o); }, async get(k) { return { [k]: this._d[k] }; }, async remove(k) { delete this._d[k]; } } },
    runtime: { getURL: (x) => 'chrome-extension://id/' + x, getManifest: () => ({ version: '1.8.0' }) },
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(SRC, 'utf8') + '\n;globalThis.__api = { ghCall, ctxMessage, ctxDecide, ctxAsks };', sandbox);
const api = sandbox.__api;
const page = { origin: 'https://abc.claudeusercontent.com', url: 'https://abc.claudeusercontent.com/x' };
// пользователь нажимает «Разрешить» (или «Отклонить») в окне загрузчика
function autoDecide(allow) { const t = setInterval(() => { for (const id of api.ctxAsks.keys()) { api.ctxDecide(id, allow); clearInterval(t); } }, 5); }

(async () => {
  const out = {};
  if (scenario === 'flow') {
    autoDecide(true);
    out.list = await api.ghCall(page, 'list', { repo: 'team/ctx' });
    out.asks = asks.length;
    out.grants = settings.ctxGrants;
    out.read = await api.ghCall(page, 'read', { repo: 'team/ctx', paths: ['rules/generation.md', 'нет.md'] });
    const h = out.read.files.find((f) => f.path === 'rules/generation.md').hash;
    out.c1 = await api.ghCall(page, 'commit', { repo: 'team/ctx', branch: 'main', files: [{ path: 'rules/generation.md', text: 'НОВОЕ', base: h }, { path: 'products/moi/memory.md', text: '- урок', base: null }], message: 'm1' });
    out.mainAfter = trees[commits[refs.main].tree].files['rules/generation.md'];
    out.branchAfter = trees[commits[refs[out.c1.branch]].tree].files;
    // вторая отправка из своей ветки — в ту же ветку
    out.c2 = await api.ghCall(page, 'commit', { repo: 'team/ctx', branch: out.c1.branch, base: 'main', files: [{ path: 'rules/generation.md', text: 'ЕЩЁ', base: out.c1.hashes['rules/generation.md'] }], message: 'm2' });
    out.branches = Object.keys(refs).sort();
    out.asksAfter = asks.length;
  } else if (scenario === 'conflict') {
    autoDecide(true);
    out.r = await api.ghCall(page, 'commit', { repo: 'team/ctx', branch: 'main', files: [{ path: 'rules/generation.md', text: 'X', base: 'старый' }] });
    out.branches = Object.keys(refs);
  } else if (scenario === 'deny') {
    autoDecide(false);
    try { await api.ghCall(page, 'list', { repo: 'team/ctx' }); } catch (e) { out.error = e.message; out.code = e.code; }
    out.calls = log.length;
  } else if (scenario === 'badpath') {
    settings.ctxGrants = { [page.origin]: { gh: ['team/ctx'] } };
    for (const p of ['../x.md', '.github/workflows/x.yml', 'a/../../b.md', 'run.sh']) {
      try { await api.ghCall(page, 'commit', { repo: 'team/ctx', branch: 'main', files: [{ path: p, text: 'x' }] }); out[p] = 'written'; } catch (e) { out[p] = e.code; }
    }
  } else if (scenario === 'notoken') {
    settings = { ...settings, ghToken: '', ctxGrants: { [page.origin]: { gh: ['team/ctx'] } } };
    try { await api.ghCall(page, 'list', { repo: 'team/ctx' }); } catch (e) { out.error = e.message; out.code = e.code; }
  } else if (scenario === 'pages') {
    // страницы QA pro не могут ни решать за пользователя, ни смотреть разрешения — это проверяет background.js; здесь — CTX_PING
    out.ping = await api.ctxMessage({ type: 'CTX_PING' }, page);
  }
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
})().catch((e) => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(1); });
