// Мост 1.1: ядро переживает обёртку (приложение Claude), задания хранятся на диске.
const { spawn } = require('child_process'), http = require('http'), crypto = require('crypto'), path = require('path'), fs = require('fs'), os = require('os');
const PORT = 47900 + Math.floor(Math.random() * 90), DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'qpb-'));
const ENV = { ...process.env, QA_PRO_BRIDGE_PORT: String(PORT), QA_PRO_BRIDGE_DIR: DIR };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function wrapper() {
  const p = spawn(process.execPath, [path.join(__dirname, '../bridge/qa-pro-bridge/server/index.js')], { env: ENV });
  let out = ''; const pend = new Map(); let nid = 1;
  p.stdout.on('data', (d) => { out += d; let i; while ((i = out.indexOf('\n')) >= 0) { const l = out.slice(0, i); out = out.slice(i + 1); const m = JSON.parse(l); pend.get(m.id)?.(m); pend.delete(m.id); } });
  p.stderr.on('data', (d) => process.stdout.write('   wrap: ' + d));
  const rpc = (method, params) => new Promise((r) => { const id = nid++; pend.set(id, r); p.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); });
  const tool = async (name, args) => { const r = (await rpc('tools/call', { name, arguments: args })).result; return r.isError ? { error: r.content[0].text } : r.structuredContent; };
  return { p, rpc, tool };
}
const health = () => new Promise((r) => http.get({ host: '127.0.0.1', port: PORT, path: '/health', timeout: 800 }, (res) => { let s = ''; res.on('data', (c) => s += c); res.on('end', () => r(JSON.parse(s))); }).on('error', () => r(null)));
function wsConnect() {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port: PORT, path: '/ext', headers: { Connection: 'Upgrade', Upgrade: 'websocket', 'Sec-WebSocket-Key': crypto.randomBytes(16).toString('base64'), 'Sec-WebSocket-Version': '13', Origin: 'chrome-extension://abcdefghijklmnopabcdefghijklmnop' } });
    req.on('upgrade', (res, sock) => {
      const msgs = []; let buf = Buffer.alloc(0);
      sock.on('data', (d) => { buf = Buffer.concat([buf, d]); while (buf.length >= 2) { let len = buf[1] & 0x7f, off = 2; if (len === 126) { len = buf.readUInt16BE(2); off = 4; } if (buf.length < off + len) break; msgs.push(JSON.parse(buf.subarray(off, off + len).toString())); buf = buf.subarray(off + len); } });
      const send = (o) => { const p = Buffer.from(JSON.stringify(o)); const mask = crypto.randomBytes(4); const head = p.length < 126 ? Buffer.from([0x81, 0x80 | p.length]) : Buffer.from([0x81, 0x80 | 126, p.length >> 8, p.length & 255]); sock.write(Buffer.concat([head, mask, Buffer.from(p.map((b, i) => b ^ mask[i & 3]))])); };
      resolve({ msgs, send, sock });
    });
    req.on('response', (res) => reject(new Error('HTTP ' + res.statusCode))); req.on('error', reject); req.end();
  });
}
(async () => {
  const A = wrapper(); await A.rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
  const p1 = await A.tool('ping', {});
  console.log('C1 ping:', p1.version, p1.mode, p1.core, '| pid', (await health())?.pid);
  const up = await A.tool('sfera_upload', { title: 'T', cases: [{ ref: 'u1', name: 'Кейс' }] });
  console.log('C2 queued:', up.status);
  A.p.stdin.end(); await sleep(500);
  console.log('C3 app closed → core alive:', !!(await health()), '| wrapper exited:', A.p.exitCode !== null);
  const ws = await wsConnect(); ws.send({ t: 'hello', version: '1.4.0' }); await sleep(300);
  console.log('C4 ext got job while app closed:', ws.msgs.filter((m) => m.t === 'job').length);
  ws.send({ t: 'opened', id: up.jobId }); ws.send({ t: 'result', id: up.jobId, results: [{ ref: 'u1', ok: true, code: 'PPAN-T7' }], section: { projectCode: 'PPAN', sectionId: 1 } }); await sleep(300);
  console.log('C5 acks:', ws.msgs.filter((m) => m.t === 'ack').map((m) => m.kind).join(','), '| saved on disk:', JSON.parse(fs.readFileSync(path.join(DIR, 'jobs.json'))).find((j) => j.id === up.jobId)?.status);
  // перезапуск ядра (перезагрузка компьютера): задания восстанавливаются с диска
  const token = fs.readFileSync(path.join(DIR, 'token'), 'utf8');
  await new Promise((r) => { const q = http.request({ host: '127.0.0.1', port: PORT, method: 'POST', path: '/shutdown', headers: { 'x-qa-pro-bridge-token': token } }, (res) => { res.resume(); res.on('end', r); }); q.end(); });
  await sleep(400); console.log('C6 core stopped:', !(await health()));
  const B = wrapper(); await B.rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
  const j = await B.tool('sfera_job', { jobId: up.jobId });
  console.log('C7 after restart:', j.status, JSON.stringify(j.results), '| core', (await B.tool('ping', {})).core);
  // защита: чужой вызов без секрета и вызов «со страницы сайта»
  const bad = await new Promise((r) => { const q = http.request({ host: '127.0.0.1', port: PORT, method: 'POST', path: '/rpc', headers: { 'Content-Type': 'application/json' } }, (res) => { res.resume(); r(res.statusCode); }); q.end('{"tool":"ping"}'); });
  const site = await new Promise((r) => { const q = http.request({ host: '127.0.0.1', port: PORT, method: 'POST', path: '/rpc', headers: { 'Content-Type': 'application/json', 'x-qa-pro-bridge-token': token, Origin: 'https://evil.example' } }, (res) => { res.resume(); r(res.statusCode); }); q.end('{"tool":"ping"}'); });
  console.log('C8 no token:', bad, '| from website:', site);
  const t2 = fs.readFileSync(path.join(DIR, 'token'), 'utf8');
  await new Promise((r) => { const q = http.request({ host: '127.0.0.1', port: PORT, method: 'POST', path: '/shutdown', headers: { 'x-qa-pro-bridge-token': t2 } }, (res) => { res.resume(); res.on('end', r); }); q.end(); });
  B.p.kill(); ws.sock.destroy(); await sleep(200); process.exit(0);
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
