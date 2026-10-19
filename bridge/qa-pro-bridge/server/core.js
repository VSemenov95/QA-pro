#!/usr/bin/env node
// QA pro — ядро локального моста. Работает отдельным фоновым процессом, поэтому переживает выход
// из приложения Claude: загрузчик в Chrome остаётся на связи, задания и результаты хранятся на диске.
//  • Загрузчику — WebSocket 127.0.0.1:<порт>/ext (только с адреса расширения браузера).
//  • Обёртке MCP (server/index.js) — POST /rpc с секретом из ~/.qa-pro-bridge/token.
// Только встроенные модули Node.js. В Сферу ядро ничего не отправляет и токенов не видит.
'use strict';
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const VERSION = '1.4.0';
const PORT = Number(process.env.QA_PRO_BRIDGE_PORT) || 47321;
const DIR = process.env.QA_PRO_BRIDGE_DIR || path.join(os.homedir(), '.qa-pro-bridge');
const MAX_WAIT = 25000;            // долгий опрос sfera_job — меньше лимита ответа приложения
const JOB_TTL = 24 * 3600e3;       // задания и результаты хранятся сутки
const HB_EVERY = 20000;            // сердцебиение: держит фоновую часть расширения активной
const IDLE_EXIT = 72 * 3600e3;     // фоновое ядро само завершится, если приложение Claude не появлялось трое суток
const TERMINAL = new Set(['done', 'cancelled', 'error']);

function start({ mode = 'standalone' } = {}) {
  const log = (...a) => { const line = `[qa-pro-bridge ${mode}] ${a.join(' ')}\n`; if (mode === 'inprocess') process.stderr.write(line); else { try { fs.appendFileSync(path.join(DIR, 'bridge.log'), new Date().toISOString() + ' ' + line); } catch { /* без журнала */ } } };
  try { fs.mkdirSync(DIR, { recursive: true, mode: 0o700 }); } catch { /* ниже станет ясно */ }


  /* ---------- секрет для обёртки MCP ---------- */
  const tokenFile = path.join(DIR, 'token');
  let token = '';
  try { token = fs.readFileSync(tokenFile, 'utf8').trim(); } catch { /* создадим */ }
  if (!/^[a-f0-9]{64}$/.test(token)) {
    token = crypto.randomBytes(32).toString('hex');
    try { fs.writeFileSync(tokenFile, token, { mode: 0o600 }); } catch (e) { log('не удалось сохранить секрет:', e.message); }
  }

  /* ---------- задания (на диске) ---------- */
  const jobsFile = path.join(DIR, 'jobs.json');
  const jobs = new Map();
  try {
    const saved = JSON.parse(fs.readFileSync(jobsFile, 'utf8'));
    for (const j of Array.isArray(saved) ? saved : []) if (j?.id && Date.now() - (j.createdAt || 0) < JOB_TTL) jobs.set(j.id, j);
  } catch { /* пусто */ }
  // задание, отданное загрузчику до перезапуска, остаётся у него: он вернёт результат после переподключения
  let saveT = null;
  const persist = () => {
    clearTimeout(saveT);
    saveT = setTimeout(() => {
      try { const tmp = jobsFile + '.tmp'; fs.writeFileSync(tmp, JSON.stringify([...jobs.values()]), { mode: 0o600 }); fs.renameSync(tmp, jobsFile); }
      catch (e) { log('не удалось сохранить задания:', e.message); }
    }, 200);
  };
  const waiters = new Set();
  function touch(job) {
    job.updatedAt = Date.now(); persist();
    for (const w of [...waiters]) if (w.id === job.id) { waiters.delete(w); clearTimeout(w.t); w.resolve(); }
  }
  function pub(job) {
    return {
      jobId: job.id, status: job.status, count: job.cases.length, title: job.title,
      results: job.results || null, section: job.section || null, error: job.error || '',
      createdAt: job.createdAt, updatedAt: job.updatedAt, extension: extInfo(),
    };
  }
  setInterval(() => {
    const now = Date.now(); let n = 0;
    for (const [id, j] of jobs) if (now - j.createdAt > JOB_TTL) { jobs.delete(id); n++; }
    if (n) persist();
  }, 600e3).unref();

  /* ---------- WebSocket для загрузчика ---------- */
  let ext = null, lastExtSeen = 0, listening = false, listenError = '', lastMcp = Date.now();
  const extInfo = () => (ext ? { connected: true, version: ext.version || '', since: ext.since, baseUrl: ext.baseUrl || '' } : { connected: false, lastSeen: lastExtSeen || null });
  function frame(payload, op = 0x1) {
    const len = payload.length;
    let head;
    if (len < 126) head = Buffer.from([0x80 | op, len]);
    else if (len < 65536) { head = Buffer.alloc(4); head[0] = 0x80 | op; head[1] = 126; head.writeUInt16BE(len, 2); }
    else { head = Buffer.alloc(10); head[0] = 0x80 | op; head[1] = 127; head.writeBigUInt64BE(BigInt(len), 2); }
    return Buffer.concat([head, payload]);
  }
  function wsSend(conn, obj) {
    if (!conn || conn.sock.destroyed) return false;
    try { conn.sock.write(frame(Buffer.from(JSON.stringify(obj), 'utf8'))); return true; } catch { return false; }
  }
  function parseFrames(conn) {
    for (;;) {
      const b = conn.buf;
      if (b.length < 2) return;
      const fin = b[0] & 0x80, op = b[0] & 0x0f, masked = b[1] & 0x80;
      let len = b[1] & 0x7f, off = 2;
      if (len === 126) { if (b.length < 4) return; len = b.readUInt16BE(2); off = 4; }
      else if (len === 127) { if (b.length < 10) return; len = Number(b.readBigUInt64BE(2)); off = 10; }
      if (len > 32 * 1024 * 1024) { conn.sock.destroy(); return; }
      const maskAt = off;
      if (masked) off += 4;
      if (b.length < off + len) return;
      const payload = Buffer.from(b.subarray(off, off + len));
      if (masked) for (let i = 0; i < payload.length; i++) payload[i] ^= b[maskAt + (i & 3)];
      conn.buf = b.subarray(off + len);
      if (op === 0x8) { try { conn.sock.end(frame(Buffer.alloc(0), 0x8)); } catch { /* закрыт */ } return; }
      if (op === 0x9) { try { conn.sock.write(frame(payload, 0xA)); } catch { /* закрыт */ } continue; }
      if (op === 0xA || op === 0x2) continue;
      conn.frag = op === 0x1 ? [payload] : [...(conn.frag || []), payload];
      if (fin) { const text = Buffer.concat(conn.frag).toString('utf8'); conn.frag = null; onExtMessage(conn, text); }
    }
  }
  function flushQueued() {
    if (!ext) return;
    for (const j of jobs.values()) {
      if (j.status !== 'queued') continue;
      if (wsSend(ext, { t: 'job', id: j.id, title: j.title, cases: j.cases })) { j.status = 'sent'; touch(j); }
    }
  }
  function onExtMessage(conn, text) {
    let m;
    try { m = JSON.parse(text); } catch { return; }
    conn.lastSeen = Date.now();
    if (m.t === 'hello') { conn.version = String(m.version || '').slice(0, 20); conn.baseUrl = String(m.baseUrl || '').slice(0, 200); flushQueued(); return; }
    if (m.t === 'hb') return;
    if (m.t === 'call_result') {
      const c = calls.get(String(m.id || ''));
      if (!c) return;
      calls.delete(m.id); clearTimeout(c.t);
      if (m.ok) c.resolve({ ok: true, data: m.data ?? null }); else c.reject(Object.assign(new Error(String(m.error || 'Загрузчик вернул ошибку.').slice(0, 600)), { code: m.code || '' }));
      return;
    }
    const job = jobs.get(String(m.id || ''));
    if (m.id) wsSend(conn, { t: 'ack', id: m.id, kind: m.t }); // загрузчик убирает сообщение из своей очереди
    if (!job || TERMINAL.has(job.status)) return;
    if (m.t === 'opened') { job.status = 'opened'; touch(job); }
    else if (m.t === 'result') {
      job.status = 'done';
      job.results = (Array.isArray(m.results) ? m.results : []).map((r) => ({ ref: r.ref ?? null, ok: !!r.ok, code: String(r.code || ''), status: r.status || 0, error: String(r.error || '').slice(0, 300) }));
      job.section = m.section || null; touch(job);
    } else if (m.t === 'cancelled') { job.status = 'cancelled'; touch(job); }
    else if (m.t === 'error') { job.status = 'error'; job.error = String(m.error || '').slice(0, 500); touch(job); }
  }

  /* ---------- операции API Сферы через загрузчик (дефекты в Сфера.Задачи, импорт репозитория) ---------- */
  const calls = new Map();
  function extCall(op, args, timeout = 25000) {
    if (!ext) return Promise.reject(new Error('Загрузчик Сферы в Chrome не подключён к мосту: откройте Chrome с загрузчиком и включите в его настройках связь с приложением Claude.'));
    const id = 'mc-' + Date.now().toString(36) + crypto.randomBytes(3).toString('hex');
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => { calls.delete(id); reject(new Error('Загрузчик не ответил за ' + Math.round(timeout / 1000) + ' с.')); }, timeout);
      calls.set(id, { resolve, reject, t });
      if (!wsSend(ext, { t: 'call', id, op, args })) { clearTimeout(t); calls.delete(id); reject(new Error('Не удалось передать запрос загрузчику.')); }
    });
  }

  /* ---------- локальный репозиторий автотестов: только внутри выбранной пользователем папки ---------- */
  const SKIP_DIRS = new Set(['.git', 'node_modules', 'build', 'target', 'out', '.idea', '.gradle', '.vscode', 'allure-results', 'allure-report', '.mvn']);
  const TEXT_EXT = /\.(java|kt|kts|groovy|gradle|xml|properties|ya?ml|json|md|txt|conf|feature|sql|csv)$/i;
  function rootOf(args) {
    const root = String(args.root || '').trim();
    if (!root || !path.isAbsolute(root)) throw new Error('Укажите полный путь к папке репозитория, например C:\\work\\autotests или /home/me/autotests.');
    let real;
    try { real = fs.realpathSync(root); } catch { throw new Error('Папка не найдена: ' + root); }
    if (!fs.statSync(real).isDirectory()) throw new Error('Это не папка: ' + root);
    return real;
  }
  function inside(root, rel) {
    const relStr = String(rel || '');
    if (!relStr || path.isAbsolute(relStr) || /^[\\/]|^[a-zA-Z]:/.test(relStr)) throw new Error('Путь вне папки репозитория: ' + rel);
    const p = path.resolve(root, relStr);
    const r = path.relative(root, p);
    if (!r || r.startsWith('..') || path.isAbsolute(r)) throw new Error('Путь вне папки репозитория: ' + rel);
    let probe = p;
    while (!fs.existsSync(probe)) probe = path.dirname(probe);
    const realProbe = fs.realpathSync(probe), rr = path.relative(root, realProbe);
    if (rr.startsWith('..') || path.isAbsolute(rr)) throw new Error('Путь ведёт за пределы папки репозитория: ' + rel);
    return p;
  }
  function listFiles(root, max = 4000) {
    const out = [];
    const walk = (dir) => {
      let items = [];
      try { items = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
      for (const d of items) {
        if (out.length >= max) return;
        if (d.isSymbolicLink()) continue;
        const full = path.join(dir, d.name);
        if (d.isDirectory()) { if (!SKIP_DIRS.has(d.name) && !d.name.startsWith('.')) walk(full); continue; }
        if (!TEXT_EXT.test(d.name)) continue;
        let size = 0; try { size = fs.statSync(full).size; } catch { continue; }
        out.push({ path: path.relative(root, full).split(path.sep).join('/'), size });
      }
    };
    walk(root);
    return out;
  }

  /* ---------- инструменты ---------- */
  const str = (v, n) => String(v ?? '').slice(0, n);
  async function callTool(name, args = {}, { fromExt = false } = {}) {
    if (!fromExt) lastMcp = Date.now();
    if (name === 'ping') return { ok: true, name: 'qa-pro-bridge', version: VERSION, mode, port: PORT, listening, error: listenError, extension: extInfo(), pending: [...jobs.values()].filter((j) => !TERMINAL.has(j.status)).length };
    if (name === 'sfera_upload') {
      if (!listening) throw new Error(listenError || 'Мост не слушает порт — перезапустите приложение Claude.');
      const cases = Array.isArray(args.cases) ? args.cases.slice(0, 2000) : [];
      if (!cases.length) throw new Error('Нет тест-кейсов для загрузки.');
      const clean = cases.filter((c) => c && typeof c === 'object').map((c) => ({
        ref: c.ref == null ? null : str(c.ref, 100), qaId: str(c.qaId, 60), name: str(c.name, 256), description: str(c.description, 20000),
        preConditions: Array.isArray(c.preConditions) ? c.preConditions : [], steps: Array.isArray(c.steps) ? c.steps : [],
        postConditions: Array.isArray(c.postConditions) ? c.postConditions : [], priority: str(c.priority, 20),
        suites: Array.isArray(c.suites) ? c.suites.map((x) => str(x, 40)) : [],
      }));
      const id = 'mj-' + Date.now().toString(36) + crypto.randomBytes(3).toString('hex');
      const job = { id, title: str(args.title, 200) || 'QA pro', cases: clean, status: 'queued', createdAt: Date.now(), updatedAt: Date.now() };
      jobs.set(id, job); persist();
      flushQueued();
      return pub(job);
    }
    if (name === 'sfera_job') {
      const job = jobs.get(str(args.jobId, 60));
      if (!job) throw new Error('Задание не найдено: оно старше суток или мост переустанавливали.');
      const wait = Math.min(Math.max(Number(args.waitMs) || 0, 0), MAX_WAIT);
      const since = Number(args.since) || 0;
      if (wait && !TERMINAL.has(job.status) && job.updatedAt <= since) {
        await new Promise((resolve) => { const w = { id: job.id, resolve }; w.t = setTimeout(() => { waiters.delete(w); resolve(); }, wait); waiters.add(w); });
      }
      return pub(job);
    }
    if (name === 'sfera_cancel') {
      const job = jobs.get(str(args.jobId, 60));
      if (!job) throw new Error('Задание не найдено.');
      if (!TERMINAL.has(job.status)) {
        if (job.status !== 'queued') wsSend(ext, { t: 'cancel', id: job.id });
        job.status = 'cancelled'; job.cancelledBy = 'app'; touch(job);
      }
      return pub(job);
    }
    if (name === 'sfera_call') {
      const op = str(args.op, 60);
      if (!/^(tasks|repo)\.[a-zA-Z]+$/.test(op)) throw new Error('Неизвестная операция Сферы: ' + op);
      return extCall(op, args.args && typeof args.args === 'object' ? args.args : {}, Math.min(Math.max(Number(args.timeoutMs) || 25000, 1000), 25000));
    }
    if (name === 'project_list') {
      const root = rootOf(args);
      const files = listFiles(root, Math.min(Number(args.max) || 4000, 6000));
      return { root, name: path.basename(root), files };
    }
    if (name === 'project_read') {
      const root = rootOf(args);
      const paths = (Array.isArray(args.paths) ? args.paths : []).slice(0, 400).map((x) => str(x, 400));
      let total = 0; const files = [];
      for (const rel of paths) {
        const p = inside(root, rel);
        let text = '';
        try { const st = fs.statSync(p); if (st.size > 300000) { files.push({ path: rel, error: 'файл больше 300 КБ' }); continue; } text = fs.readFileSync(p, 'utf8'); }
        catch { files.push({ path: rel, error: 'не прочитан' }); continue; }
        if (total + text.length > 3e6) { files.push({ path: rel, error: 'превышен объём за один запрос' }); continue; }
        total += text.length; files.push({ path: rel, text });
      }
      return { files };
    }
    if (name === 'project_write') {
      const root = rootOf(args);
      const list = (Array.isArray(args.files) ? args.files : []).slice(0, 100);
      if (!list.length) throw new Error('Нет файлов для записи.');
      const written = [];
      for (const f of list) {
        const rel = str(f?.path, 400);
        if (!/\.(java|kt|kts|groovy|properties|json|ya?ml|xml|md|feature)$/i.test(rel)) throw new Error('Запись такого файла не разрешена: ' + rel);
        const p = inside(root, rel), existed = fs.existsSync(p);
        fs.mkdirSync(path.dirname(p), { recursive: true });
        fs.writeFileSync(p, String(f?.content ?? ''), 'utf8');
        written.push({ path: rel, created: !existed });
      }
      return { root, written };
    }
    throw new Error('Неизвестный инструмент: ' + name);
  }

  /* ---------- HTTP: здоровье, вызовы обёртки, WebSocket ---------- */
  const json = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(obj)); };
  const authed = (req) => !req.headers.origin && crypto.timingSafeEqual(Buffer.from(String(req.headers['x-qa-pro-bridge-token'] || '').padEnd(64).slice(0, 64)), Buffer.from(token));
  const server = http.createServer((req, res) => {
    if (req.method === 'GET' && req.url === '/health') return json(res, 200, { ok: true, name: 'qa-pro-bridge', version: VERSION, mode, pid: process.pid });
    if (req.method !== 'POST' || !['/rpc', '/shutdown'].includes(req.url)) return json(res, 404, { error: 'not found' });
    if (!authed(req)) return json(res, 403, { error: 'forbidden' });
    if (req.url === '/shutdown') {
      json(res, 200, { ok: true });
      if (mode === 'standalone') setTimeout(() => process.exit(0), 100);
      return;
    }
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (c) => { body += c; if (body.length > 8e6) req.destroy(); });
    req.on('end', async () => {
      let m;
      try { m = JSON.parse(body || '{}'); } catch { return json(res, 400, { error: 'bad json' }); }
      try { json(res, 200, { ok: true, result: await callTool(String(m.tool || ''), m.args || {}) }); }
      catch (e) { json(res, 200, { ok: false, error: String(e?.message || e) }); }
    });
  });
  server.on('upgrade', (req, sock) => {
    const origin = String(req.headers.origin || '');
    if (req.url !== '/ext' || !/^(chrome-extension|extension):\/\/[a-z]+$/i.test(origin) || String(req.headers.upgrade || '').toLowerCase() !== 'websocket' || !req.headers['sec-websocket-key']) {
      sock.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');
      return;
    }
    const accept = crypto.createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n\r\n');
    sock.setNoDelay(true);
    const conn = { sock, buf: Buffer.alloc(0), frag: null, version: '', baseUrl: '', since: Date.now(), lastSeen: Date.now() };
    if (ext && ext.sock !== sock) { try { ext.sock.destroy(); } catch { /* уже закрыт */ } }
    ext = conn;
    log('загрузчик подключился', origin);
    sock.on('data', (d) => { conn.buf = Buffer.concat([conn.buf, d]); parseFrames(conn); });
    sock.on('end', () => { try { sock.end(); } catch { /* уже закрыт */ } });
    sock.on('close', () => { if (ext === conn) { ext = null; lastExtSeen = Date.now(); log('загрузчик отключился'); } });
    sock.on('error', () => { /* закрытие обработает close */ });
    flushQueued();
  });
  const hb = setInterval(() => {
    if (ext) {
      if (Date.now() - ext.lastSeen > 3 * HB_EVERY) { try { ext.sock.destroy(); } catch { /* уже закрыт */ } }
      else wsSend(ext, { t: 'hb', at: Date.now() });
    }
    if (mode === 'standalone' && Date.now() - lastMcp > IDLE_EXIT) { log('приложение Claude давно не появлялось — завершаюсь'); process.exit(0); }
  }, HB_EVERY);
  hb.unref?.();
  const ready = new Promise((resolve) => {
    server.on('error', (e) => {
      listening = false;
      listenError = e.code === 'EADDRINUSE' ? `Порт ${PORT} занят другой программой.` : String(e.message || e);
      log(listenError);
      resolve({ ok: false, error: listenError });
      if (mode === 'standalone') process.exit(1);
    });
    server.listen(PORT, '127.0.0.1', () => { listening = true; listenError = ''; log('слушаю 127.0.0.1:' + PORT, 'v' + VERSION); resolve({ ok: true }); });
  });
  if (mode === 'standalone') { process.on('uncaughtException', (e) => log('ошибка:', e?.stack || e)); setInterval(() => {}, 1 << 30); }
  return { callTool, ready, token: () => token };
}

module.exports = { start, VERSION, PORT, DIR };
if (require.main === module) start({ mode: 'standalone' });
